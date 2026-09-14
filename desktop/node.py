"""Durable per-device connector and desktop operations."""
import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from delivery import Delivery, dispatch_one
from desktop.protocol import Database, Hub, MAX_QUEUE, VERSION, encoded, require, uid


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('redirect refused; confirm the hub URL')


def hub_url(url, allow_loopback=False):
    parsed = urllib.parse.urlparse(url)
    require(parsed.scheme == 'https' or (allow_loopback and parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost')), 'remote hub requires HTTPS')
    require(parsed.hostname and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment and parsed.path in ('', '/'), 'use a hub origin without credentials or path')
    return url.rstrip('/')


class Remote:
    def __init__(self, url, token='', allow_loopback=False):
        self.url = hub_url(url, allow_loopback)
        self.token = token

    def call(self, action, data=None):
        request = urllib.request.Request(self.url+'/v1/'+action, data=encoded(data or {}).encode(),
                                        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer '+self.token})
        try:
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=32) as response:
                payload=response.read(2_000_001)
                require(len(payload)<=2_000_000, 'hub response exceeds protocol byte limit')
                return json.loads(payload)
        except urllib.error.HTTPError as exc:
            # Never surface response bodies, URLs or native credentials in logs.
            if exc.code in (400, 401, 403, 409):
                raise ValueError('hub rejected request (%s); verify pairing, identity and version' % exc.code) from None
            raise ConnectionError('hub unavailable') from None


def hub_call(hub, token, action, data):
    if action == 'pair-request':
        return hub.pair_request(data['id'], data['proof'], data['name'], data['device'])
    if action == 'pair-finish':
        return hub.pair_finish(data['id'], data['proof'], data['device'], data['token'])
    actor = hub.auth(token)
    room = data.get('room', 'general')
    if action == 'snapshot':
        return hub.snapshot(actor, room, data.get('cursor'))
    if action == 'events':
        return {'events': hub.stream(actor, room, data.get('after', 0), data.get('timeout', 0))}
    if action == 'event':
        return hub.event(actor, data)
    if action == 'bind':
        return hub.bind(actor, room, data['native'], data['app'], data['title'], data.get('generation', 1))
    if action == 'pair-create':
        return hub.pair_create(actor, room)
    if action == 'pair-approve':
        return hub.pair_approve(actor, data['id'])
    if action == 'revoke':
        return hub.revoke(actor, data['device'], room)
    raise ValueError('unknown protocol action')


class Node(Database):
    def __init__(self, root, vault, allow_loopback=False):
        self.root, self.vault = Path(root).resolve(), vault
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        super().__init__(str(self.root/'device.sqlite3'))
        require(self.db.execute('PRAGMA user_version').fetchone()[0] in (0, 1), 'device schema newer than app')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY, event TEXT, state TEXT, error TEXT);
        CREATE TABLE IF NOT EXISTS cache(seq INTEGER PRIMARY KEY, id TEXT UNIQUE, event TEXT);
        CREATE TABLE IF NOT EXISTS bindings(id TEXT PRIMARY KEY, data TEXT, paused INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS offered(binding TEXT PRIMARY KEY, seq INTEGER DEFAULT 0, cursor INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY, state TEXT);
        PRAGMA user_version=1;
        ''')
        self.db.execute("UPDATE outbox SET state='saved' WHERE state='sending'")
        self.db.commit()
        self.hub = None
        self.allow_loopback = allow_loopback
        self.online = False
        self.error = ''
        self.stop = threading.Event()
        self.work = threading.Event()
        self.bridge_condition = threading.Condition()
        self.bridge_leases = {}
        self.bridge_seen = {}
        self.delivery = Delivery(str(self.root))
        if not self.get('device'):
            self.put('device', uid())
        if self.get('mode') == 'host':
            self.hub = Hub(str(self.root/'hub.sqlite3'))
        # A new process fences old native bridges. Native identities remain intact.
        for binding in self.bindings():
            binding['generation'] += 1
            self.save_binding(binding)
            self.delivery.register(binding['id'], binding['room'], binding['app'], binding['app'], binding['native'] if binding['app'] == 'codex-queue' else '')
        self.threads = []

    def get(self, key, default=None):
        rows = self.rows('SELECT value FROM settings WHERE key=?', (key,))
        return json.loads(rows[0]['value']) if rows else default

    def put(self, key, value):
        with self.lock, self.db:
            self.db.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, encoded(value)))

    def credential(self):
        token = self.vault.get('device')
        require(token, 'device credential missing in Keychain')
        return token

    def call(self, action, data=None):
        if self.hub:
            return hub_call(self.hub, self.credential(), action, data or {})
        return Remote(self.get('hub_url'), self.credential(), self.allow_loopback).call(action, data)

    def setup(self, name):
        require(not self.get('mode'), 'device already configured')
        require(isinstance(name, str) and 0 < len(name) <= 80, 'device name required')
        token = secrets.token_urlsafe(48)
        self.vault.set('device', token)
        self.hub = Hub(str(self.root/'hub.sqlite3'))
        self.hub.bootstrap(name, token, self.get('device'))
        self.put('name', name)
        self.put('room', 'general')
        self.put('mode', 'host')
        self.online = True
        self.work.set()
        return {'created': True}

    def join_request(self, url, pairing, proof, name):
        require(not self.get('mode'), 'use a separate device profile to join another hub')
        remote = Remote(url, allow_loopback=self.allow_loopback)
        self.vault.set('pair-proof', proof)
        self.vault.set('device', secrets.token_urlsafe(48))
        self.put('hub_url', remote.url)
        self.put('pair_id', pairing)
        self.put('name', name)
        return remote.call('pair-request', {'id': pairing, 'proof': proof, 'name': name, 'device': self.get('device')})

    def join_finish(self):
        remote = Remote(self.get('hub_url'), allow_loopback=self.allow_loopback)
        result = remote.call('pair-finish', {'id': self.get('pair_id'), 'proof': self.vault.get('pair-proof'), 'device': self.get('device'), 'token': self.credential()})
        self.put('mode', 'member')
        self.put('room', result['room'])
        self.work.set()
        return {'joined': True}

    def bindings(self):
        return [dict(json.loads(r['data']), paused=bool(r['paused'])) for r in self.rows('SELECT * FROM bindings')]

    def save_binding(self, binding):
        with self.lock, self.db:
            self.db.execute('INSERT INTO bindings VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data,paused=excluded.paused', (binding['id'], encoded(binding), int(binding.get('paused', False))))

    def bind(self, data):
        native, app = data['native'].strip(), data['app']
        directory = data.get('directory', '').strip()
        if app == 'opencode-bridge':
            require(directory and Path(directory).is_absolute() and Path(directory).is_dir(), 'OpenCode requires its exact existing local directory')
        existing = next((b for b in self.bindings() if b['native'] == native and b['app'] == app), None)
        binding = self.call('bind', {'native': native, 'app': app, 'title': data['title'], 'room': self.get('room', 'general'), 'generation': existing['generation'] if existing else 1})
        if app == 'opencode-bridge':
            require(not existing or existing.get('directory') == directory, 'native workspace binding is immutable')
            binding['directory'] = directory
        self.save_binding(binding)
        self.delivery.register(binding['id'], binding['room'], app, app, native if app == 'codex-queue' else '')
        self.work.set()
        return binding

    def enqueue(self, kind, body, sender='', event_id=None):
        require(self.get('mode'), 'create or join a room first')
        binding = self.binding(sender) if sender else None
        event = {'version': VERSION, 'id': event_id or uid(), 'room': self.get('room', 'general'), 'sender': sender,
                 'generation': binding['generation'] if binding else None, 'kind': kind, 'body': body}
        require(len(encoded(event).encode('utf-8')) <= 205_000, 'event too large')
        with self.lock, self.db:
            old = self.db.execute('SELECT event FROM outbox WHERE id=?', (event['id'],)).fetchone()
            if old:
                require(old[0] == encoded(event), 'local idempotency ID reused for different content')
            else:
                require(self.db.execute("SELECT count(*) FROM outbox WHERE state='saved'").fetchone()[0] < MAX_QUEUE, 'outbox full; reconnect or cancel unsent messages')
                self.db.execute('INSERT INTO outbox VALUES(?,?,?,?)', (event['id'], encoded(event), 'saved', ''))
        self.work.set()
        return {'id': event['id'], 'state': 'saved', 'event': event}

    def binding(self, identity):
        binding = next((b for b in self.bindings() if b['id'] == identity), None)
        require(binding is not None, 'session is not bound on this device')
        return binding

    def sync_once(self):
        if not self.get('mode'):
            return
        for binding in self.bindings():
            self.call('bind', {k: binding[k] for k in ('native', 'app', 'title', 'room', 'generation')})
        for row in self.rows("SELECT * FROM outbox WHERE state='saved' ORDER BY rowid LIMIT 100"):
            with self.lock, self.db:
                claimed = self.db.execute("UPDATE outbox SET state='sending' WHERE id=? AND state='saved'", (row['id'],)).rowcount
            if not claimed:
                continue
            event = json.loads(row['event'])
            if event['sender']:
                # Unsent events from the same native identity can renew the fencing
                # generation; ID/body/target remain unchanged.
                event['generation'] = self.binding(event['sender'])['generation']
            try:
                result = self.call('event', event)
            except ValueError as exc:
                with self.lock, self.db:
                    self.db.execute("UPDATE outbox SET state='failed',error=? WHERE id=?", (str(exc), row['id']))
            except Exception:
                with self.lock, self.db:
                    self.db.execute("UPDATE outbox SET state='saved' WHERE id=?", (row['id'],))
                raise
            else:
                with self.lock, self.db:
                    self.db.execute("UPDATE outbox SET state='sent',error='' WHERE id=?", (row['id'],))
        events = self.call('events', {'room': self.get('room'), 'after': self.get('cursor', 0)})['events']
        self.receive(events)
        snapshot = {}
        cursor = None
        while True:
            page = self.call('snapshot', {'room': self.get('room'), 'cursor': cursor})
            for key,value in page.items():
                if key != 'next':snapshot.setdefault(key,[]).extend(value)
            cursor = page.get('next')
            if not cursor:break
        self.put('snapshot', snapshot)
        self.online, self.error = True, ''

    def receive(self, events):
        # Commit complete network pages and stream cursor together. On crash before
        # delivery.route, the entire cache is reconciled below using stable IDs.
        with self.lock, self.db:
            for event in events:
                self.db.execute('INSERT OR IGNORE INTO cache VALUES(?,?,?)', (event['seq'], event['id'], encoded(event)))
            if events:
                self.db.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', ('cursor', encoded(max(self.get('cursor', 0), events[-1]['seq']))))
        self.route_cache()

    def route_cache(self):
        bindings = {b['id']: b for b in self.bindings()}
        for row in self.rows('SELECT event FROM cache ORDER BY seq'):
            event = json.loads(row['event'])
            if event['kind'] != 'message':
                continue
            for target in event['body'].get('targets', []):
                if target not in bindings:
                    continue
                binding = bindings[target]
                state = 'unavailable' if binding['app'] == 'pull' else 'pending'
                self.delivery.route({'id': event['id'], 'channel': binding['room'], 'human': not event['sender'],
                    'delivery_targets': [{'session': target, 'state': state, 'reason': 'Pull only; open this session to read' if state == 'unavailable' else ''}]})
        with self.bridge_condition:
            self.bridge_condition.notify_all()

    def source_message(self, room, message):
        rows = self.rows('SELECT event FROM cache WHERE id=?', (message,))
        if not rows:
            return None
        event = json.loads(rows[0]['event'])
        return {'id': event['id'], 'channel': room, 'from': event['sender'] or 'person', 'from_session': event['sender'],
                'text': event['body']['text'], 'reply_to': event['body'].get('reply_to'),
                'note': 'This is the separate Agent Room desktop room. Use its configured room tools. If this host has only the older live-room tools, do not send an acknowledgement to the wrong server.',
                'desktop_home': str(self.root),
                'desktop_helper': os.path.realpath(__import__('sys').executable) if getattr(__import__('sys'), 'frozen', False) else str(Path(__file__).resolve().parent.parent/'desktop_main.py')}

    def report(self):
        for row in self.delivery.status(self.get('room', 'general')):
            state = row['state']
            if state in ('sending', 'relaying'):
                continue
            previous = self.rows('SELECT state FROM reports WHERE id=?', (row['id'],))
            if previous and previous[0]['state'] == state:
                continue
            self.enqueue('receipt', {'message': row['message'], 'target': row['session'], 'state': state, 'reason': row['reason'],
                         'revision': row['revision'], 'recovered_unsent': state=='pending' and row['reason']=='Reconnected; never submitted'},
                         row['session'], event_id='receipt:'+row['id']+':'+str(row['revision']))
            with self.lock, self.db:
                self.db.execute('INSERT INTO reports VALUES(?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state', (row['id'], state))

    def start(self):
        def send_loop():
            backoff = 1
            while not self.stop.is_set():
                try:
                    self.sync_once()
                    self.report()
                    backoff = 1
                except Exception:
                    self.online, self.error = False, 'Connection unavailable. Messages remain saved on this Mac.'
                    backoff = min(30, backoff*2)
                self.work.wait(backoff if not self.online else 1)
                self.work.clear()

        def stream_loop():
            while not self.stop.is_set():
                if not self.get('mode') or not self.online:
                    self.stop.wait(1)
                    continue
                try:
                    events = self.call('events', {'room': self.get('room'), 'after': self.get('cursor', 0), 'timeout': 25})['events']
                    self.receive(events)
                    self.work.set()
                except Exception:
                    self.stop.wait(3)

        def dispatch_loop():
            from desktop.mcp import incoming
            while not self.stop.is_set():
                try:
                    if self.online and not self.get('paused', False):
                        # Paused sessions stay registered and queued without being
                        # re-routed. Do not mark them closed and lose pending work.
                        paused = [b['id'] for b in self.bindings() if b.get('paused') or b.get('transport')=='local-room']
                        dispatch_one(self.delivery, self.source_message, incoming, paused)
                        self.report()
                except Exception:
                    self.error = 'Delivery needs attention. Inspect receipts; uncertain sends are not retried.'
                self.stop.wait(.5)
        for fn in (send_loop, stream_loop, dispatch_loop):
            thread = threading.Thread(target=fn, daemon=True)
            thread.start()
            self.threads.append(thread)
        from desktop.legacy import Legacy
        legacy=Legacy(self,self.get('legacy_port',8787))
        thread=threading.Thread(target=legacy.run,daemon=True)
        thread.start();self.threads.append(thread)

    def bridge_open(self, identity, native, app):
        binding = self.binding(identity)
        require(binding['native'] == native and binding['app'] == app and app in ('opencode-bridge', 'claude-channel'), 'native bridge identity mismatch')
        lease = secrets.token_urlsafe(32)
        self.bridge_leases[identity] = lease
        self.bridge_seen[identity] = time.monotonic()
        self.delivery.register(identity, binding['room'], app, app)
        with self.delivery.lock,self.delivery.db:
            self.delivery.db.execute("UPDATE deliveries SET state='pending',reason='Reconnected; never submitted',updated=? WHERE session=? AND channel=? AND attempts=0 AND state='unavailable' AND reason IN ('session closed','session closed before route was saved')",(time.time(),identity,binding['room']))
        self.work.set()
        return {'lease': lease, 'generation': binding['generation']}

    def bridge_next(self, identity, lease, timeout=20):
        binding = self.binding(identity)
        deadline = time.monotonic()+min(20, max(0, timeout))
        while True:
            require(secrets.compare_digest(self.bridge_leases.get(identity, ''), lease), 'bridge superseded; reconnect exact native session')
            self.bridge_seen[identity] = time.monotonic()
            self.delivery.heartbeat(identity, binding['room'])
            if self.online and not self.get('paused') and not binding.get('paused'):
                row = self.delivery.claim(identity, binding['room'], binding['app'])
                if row:
                    return {'delivery': row, 'message': self.source_message(binding['room'], row['message'])}
            if time.monotonic() >= deadline or self.stop.is_set():
                return {'delivery': None}
            with self.bridge_condition:
                self.bridge_condition.wait(min(1, deadline-time.monotonic()))

    def bridge_sent(self, identity, lease, delivery_id, state):
        require(secrets.compare_digest(self.bridge_leases.get(identity, ''), lease), 'stale bridge lease')
        binding = self.binding(identity)
        require(any(r['id'] == delivery_id for r in self.delivery.status(binding['room']) if r['session'] == identity), 'delivery does not belong to bridge')
        require(state in ('submitted', 'uncertain', 'unavailable'), 'invalid native send result')
        self.delivery.finish(delivery_id, state, 'Native app accepted; awaiting explicit receipt' if state == 'submitted' else 'Native send not confirmed; no automatic retry')
        self.work.set()
        return {'state': state}

    def tool(self, identity, name, args):
        binding = self.binding(identity)
        room = binding['room']
        if name == 'room_post':
            targets = [args['to_session']] if args.get('to_session') else []
            return self.enqueue('message', {'text': args['text'], 'targets': targets, 'reply_to': args.get('reply_to')}, identity, args.get('request_id'))
        if name in ('room_read', 'room_inbox'):
            cursor_rows = self.rows('SELECT * FROM offered WHERE binding=?', (identity,))
            cursor = cursor_rows[0]['cursor'] if cursor_rows else 0
            result, size = [], 0
            for row in self.rows('SELECT event FROM cache WHERE seq>? ORDER BY seq', (cursor,)):
                event = json.loads(row['event'])
                if event['kind'] != 'message':
                    continue
                if result and size+len(encoded(event)) > 40000:
                    break
                result.append(event)
                size += len(encoded(event))
            through = result[-1]['seq'] if result else cursor
            with self.lock, self.db:
                self.db.execute('INSERT INTO offered VALUES(?,?,?) ON CONFLICT(binding) DO UPDATE SET seq=max(seq,excluded.seq)', (identity, through, cursor))
            return {'messages': result, 'read_through': through, 'deliveries': self.delivery.inbox(identity, room), 'note': 'Read does not acknowledge. Acknowledge only complete messages you read.'}
        if name == 'room_ack':
            ids = args.get('delivery_ids', [])
            if args.get('read_through') is not None:
                rows = self.rows('SELECT * FROM offered WHERE binding=?', (identity,))
                require(rows and 0 <= args['read_through'] <= rows[0]['seq'], 'receipt exceeds offered complete page')
            result = self.delivery.ack(identity, room, ids)
            if args.get('read_through') is not None:
                with self.lock, self.db:
                    self.db.execute('UPDATE offered SET cursor=max(cursor,?) WHERE binding=?', (args['read_through'], identity))
            self.work.set()
            return result
        if name in ('room_sessions', 'room_context'):
            snapshot = self.get('snapshot', {})
            return {'sessions': snapshot.get('sessions', []), 'objects': snapshot.get('objects', []) if name == 'room_context' else []}
        if name == 'room_workflow':
            return self.enqueue('object', args, identity, args.get('request_id'))
        raise ValueError('unknown room tool')

    def snapshot(self):
        cached = self.get('snapshot', {})
        events = [json.loads(r['event']) for r in self.rows('SELECT event FROM cache ORDER BY seq')]
        return dict(cached, configured=bool(self.get('mode')), mode=self.get('mode'), name=self.get('name', ''),
                    device=self.get('device'), room=self.get('room', 'general'), online=self.online, error=self.error,
                    paused=self.get('paused', False), hub_url=self.get('hub_url', ''), events=events,
                    outbox=[dict(r, event=json.loads(r['event'])) for r in self.rows("SELECT * FROM outbox WHERE state<>'sent'")],
                    bindings=[dict(b, bridge_connected=time.monotonic()-self.bridge_seen.get(b['id'], -1000)<30) for b in self.bindings()])

    def control(self, action, data):
        if action in ('discover-local','bind-local'):
            from desktop.legacy import Legacy
            legacy=Legacy(self,self.get('legacy_port',8787))
            sessions=legacy.discover()
            if action=='discover-local':return {'sessions':sessions}
            exact=next((s for s in sessions if s['id']==data['session']),None)
            require(exact and exact['adapter'] in ('codex-queue','claude-channel'), 'existing push route required')
            native=exact['target'] if exact['adapter']=='codex-queue' else data['native']
            binding=self.bind({'native':native,'app':exact['adapter'],'title':data['title']})
            binding.update(transport='local-room',legacy_session=exact['id'])
            self.save_binding(binding)
            legacy.open()
            return binding
        if action == 'unlock':
            if hasattr(self.vault,'retry'):self.vault.retry()
            self.credential()
            self.work.set()
            return {'reconnecting': True}
        if action == 'backup':
            from desktop.recovery import backup
            return backup(self, self.root/'backups'/('room-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uid()[:8]))
        if action == 'snapshot':
            return self.snapshot()
        if action == 'create':
            return self.setup(data['name'])
        if action == 'join-request':
            return self.join_request(data['url'], data['id'], data['proof'], data['name'])
        if action == 'join-finish':
            return self.join_finish()
        if action == 'bind':
            return self.bind(data)
        if action in ('pair-create', 'pair-approve', 'revoke'):
            return self.call(action, dict(data, room=self.get('room', 'general')))
        if action == 'send':
            return self.enqueue('message', {'text': data['text'], 'targets': data.get('targets', []), 'reply_to': data.get('reply_to')}, event_id=data.get('id'))
        if action == 'object':
            return self.enqueue('object', data, event_id=data.get('event_id'))
        if action == 'pause':
            self.put('paused', bool(data['paused']))
            return {'paused': self.get('paused')}
        if action == 'cancel':
            with self.lock, self.db:
                changed = self.db.execute("UPDATE outbox SET state='cancelled' WHERE id=? AND state='saved'", (data['id'],)).rowcount
                require(changed, 'message already sending; cannot recall a submitted prompt')
                return {'cancelled': data['id']}
        if action == 'bridge-open':
            return self.bridge_open(data['binding'], data['native'], data['app'])
        if action == 'bridge-next':
            return self.bridge_next(data['binding'], data['lease'], data.get('timeout', 20))
        if action == 'bridge-heartbeat':
            binding=self.binding(data['binding'])
            require(secrets.compare_digest(self.bridge_leases.get(binding['id'], ''), data['lease']), 'stale bridge lease')
            self.bridge_seen[binding['id']]=time.monotonic()
            self.delivery.heartbeat(binding['id'],binding['room'])
            return {'alive': True}
        if action == 'bridge-sent':
            return self.bridge_sent(data['binding'], data['lease'], data['delivery_id'], data['state'])
        if action == 'tool':
            binding=self.binding(data['binding'])
            require(data.get('native')==binding['native'] and data.get('generation')==binding['generation'], 'native identity or connector generation changed')
            if binding['app'] in ('opencode-bridge','claude-channel'):
                require(data.get('lease') and secrets.compare_digest(data['lease'],self.bridge_leases.get(binding['id'],'')), 'stale or missing native bridge lease')
            return self.tool(data['binding'], data['name'], data.get('args', {}))
        raise ValueError('unknown local action')
