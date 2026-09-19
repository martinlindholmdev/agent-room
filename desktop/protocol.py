"""Transactional room hub. No native credentials, paths or executable commands.

Only a destination connector executes local work. All network send retries use
stable IDs. A transport receipt never implies a model has read the message.
"""
import hashlib
import json
import re
import secrets
import sqlite3
import threading
import time
import uuid

VERSION = 1
MAX_BODY = 200_000
MAX_QUEUE = 10_000
STATES = {'proposed', 'accepted', 'working', 'blocked', 'ready for review', 'resolved', 'cancelled'}
# Read-on-demand connectors: no push, no idle-wake. 'pull' is the original Claude-app
# connector; 'mcp' is the generic, self-identified connector for any MCP client.
PULL_LIKE = ('pull', 'mcp')


def uid():
    return str(uuid.uuid4())


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Database:
    def __init__(self, path):
        self.lock = threading.RLock()
        self.changed = threading.Condition(self.lock)
        self.db = sqlite3.connect(path, check_same_thread=False, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA foreign_keys=ON')

    def rows(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args)]


class Hub(Database):
    def __init__(self, path):
        super().__init__(path)
        version = self.db.execute('PRAGMA user_version').fetchone()[0]
        require(version in (0, VERSION), 'hub schema newer than this app; preserve data and upgrade')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS devices(id TEXT PRIMARY KEY, name TEXT, secret_hash TEXT,
          role TEXT, active INTEGER DEFAULT 1, created REAL);
        CREATE TABLE IF NOT EXISTS grants(device TEXT, room TEXT, PRIMARY KEY(device,room));
        CREATE TABLE IF NOT EXISTS rooms(id TEXT PRIMARY KEY, title TEXT);
        CREATE TABLE IF NOT EXISTS pairing(id TEXT PRIMARY KEY, proof_hash TEXT, expires REAL,
          room TEXT, used INTEGER DEFAULT 0, device TEXT, name TEXT, approved INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, device TEXT, room TEXT,
          native TEXT, app TEXT, title TEXT, generation INTEGER, active INTEGER,
          UNIQUE(device,room,app,native));
        CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE,
          room TEXT, device TEXT, sender TEXT, kind TEXT, body TEXT, created REAL);
        CREATE TABLE IF NOT EXISTS receipts(message TEXT, target TEXT, state TEXT, reason TEXT,
          updated REAL, PRIMARY KEY(message,target));
        CREATE TABLE IF NOT EXISTS objects(id TEXT PRIMARY KEY, room TEXT, kind TEXT,
          version INTEGER, data TEXT, author TEXT);
        CREATE TABLE IF NOT EXISTS cursors(device TEXT, room TEXT, seq INTEGER,
          PRIMARY KEY(device,room));
        PRAGMA user_version=1;
        ''')
        if 'revision' not in [r[1] for r in self.db.execute('PRAGMA table_info(receipts)')]:
            self.db.execute('ALTER TABLE receipts ADD COLUMN revision INTEGER DEFAULT -1')
            self.db.commit()

    def bootstrap(self, name, token, device=None):
        with self.lock, self.db:
            require(not self.db.execute('SELECT 1 FROM devices').fetchone(), 'hub already initialized')
            device = device or uid()
            self.db.execute('INSERT INTO devices VALUES(?,?,?,?,1,?)', (device, name, digest(token), 'admin', time.time()))
            self.db.execute('INSERT INTO rooms VALUES(?,?)', ('general', 'General'))
            self.db.execute('INSERT INTO grants VALUES(?,?)', (device, 'general'))
            return device

    def auth(self, token):
        require(isinstance(token, str) and len(token) >= 24, 'device authentication required')
        with self.lock:
            row = self.db.execute('SELECT * FROM devices WHERE secret_hash=? AND active=1', (digest(token),)).fetchone()
            require(row is not None, 'device revoked or credential invalid')
            return dict(row)

    def access(self, actor, room, admin=False):
        # Recheck revocation on every request, including open stream requests.
        require(self.db.execute('SELECT 1 FROM devices WHERE id=? AND active=1', (actor['id'],)).fetchone(), 'device revoked')
        if admin:
            require(actor['role'] == 'admin', 'trusted administrator required')
        require(self.db.execute('SELECT 1 FROM grants WHERE device=? AND room=?', (actor['id'], room)).fetchone(), 'room not granted')

    def pair_create(self, actor, room):
        with self.lock, self.db:
            self.access(actor, room, admin=True)
            pairing, proof = uid(), secrets.token_urlsafe(32)
            self.db.execute('INSERT INTO pairing VALUES(?,?,?,?,0,NULL,NULL,0)', (pairing, digest(proof), time.time()+300, room))
            return {'id': pairing, 'proof': proof, 'expires_in': 300}

    def pair_request(self, pairing, proof, name, device):
        require(isinstance(name, str) and 0 < len(name) <= 80, 'device name required')
        require(str(uuid.UUID(device)) == device, 'canonical device identity required')
        with self.lock, self.db:
            row = self.db.execute('SELECT * FROM pairing WHERE id=?', (pairing,)).fetchone()
            require(row and secrets.compare_digest(row['proof_hash'], digest(proof)) and row['expires'] > time.time() and not row['used'], 'pairing expired or invalid')
            require(row['device'] in (None, device), 'pairing already claimed')
            require(not self.db.execute('SELECT 1 FROM devices WHERE id=?', (device,)).fetchone(), 'device already exists')
            self.db.execute('UPDATE pairing SET device=?,name=? WHERE id=?', (device, name, pairing))
            return {'requested': True, 'id': pairing}

    def pair_approve(self, actor, pairing):
        with self.lock, self.db:
            row = self.db.execute('SELECT * FROM pairing WHERE id=?', (pairing,)).fetchone()
            require(row and row['device'] and row['expires'] > time.time() and not row['used'], 'no pending pairing')
            self.access(actor, row['room'], admin=True)
            self.db.execute('UPDATE pairing SET approved=1 WHERE id=?', (pairing,))
            return {'approved': True}

    def pair_finish(self, pairing, proof, device, token):
        require(len(token) >= 32, 'strong device credential required')
        with self.lock, self.db:
            row = self.db.execute('SELECT * FROM pairing WHERE id=?', (pairing,)).fetchone()
            require(row and row['device'] == device and secrets.compare_digest(row['proof_hash'], digest(proof))
                    and row['expires'] > time.time() and row['approved'], 'pairing not approved or expired')
            if row['used']:
                existing = self.db.execute('SELECT secret_hash FROM devices WHERE id=?', (device,)).fetchone()
                require(existing and secrets.compare_digest(existing[0], digest(token)), 'pairing already redeemed')
            else:
                self.db.execute('INSERT INTO devices VALUES(?,?,?,?,1,?)', (device, row['name'], digest(token), 'member', time.time()))
                self.db.execute('INSERT INTO grants VALUES(?,?)', (device, row['room']))
                self.db.execute('UPDATE pairing SET used=1 WHERE id=?', (pairing,))
            return {'device': device, 'room': row['room']}

    def revoke(self, actor, device, room):
        with self.lock, self.db:
            self.access(actor, room, admin=True)
            require(actor['id'] != device, 'cannot revoke your own administrator')
            self.db.execute('UPDATE devices SET active=0 WHERE id=?', (device,))
            self.db.execute('UPDATE sessions SET active=0,generation=generation+1 WHERE device=?', (device,))
            self.changed.notify_all()
            return {'revoked': device}

    def session_remove(self, actor, room, session):
        """Disconnect one session this same device created, e.g. when the local
        binding it backs is disconnected. Soft-deactivate like revoke() does,
        rather than deleting the row: a work/review object can carry this id
        as its exact 'owner'/'reviewer' session, and hard-deleting the row
        would make that reference permanently unresolvable (the object could
        never again be updated, even to cancel it). Also settle any receipts
        still addressed to this session -- including one caught mid-dispatch,
        which would otherwise never resolve because nothing will ever again
        report on this session's behalf -- so the inbox does not show a
        permanently unresolvable "needs connection" for a session that is
        never coming back. Idempotent: a missing or already-inactive session
        is a no-op, not an error, so a stale or already-removed binding never
        blocks local cleanup."""
        with self.lock, self.db:
            self.access(actor, room)
            row = self.db.execute('SELECT * FROM sessions WHERE id=? AND room=? AND device=?', (session, room, actor['id'])).fetchone()
            if not row or not row['active']:
                return {'removed': False}
            self.db.execute('UPDATE sessions SET active=0 WHERE id=?', (session,))
            self.db.execute("UPDATE receipts SET state='unavailable',reason='session removed',updated=?,revision=revision+1 "
                            "WHERE target=? AND state NOT IN ('acknowledged','unavailable')", (time.time(), session))
            self.changed.notify_all()
            return {'removed': True}

    def _room_slug(self, title):
        base = re.sub(r'[^a-z0-9]+', '-', title.strip().lower()).strip('-') or 'room'
        candidate, suffix = base, 1
        while self.db.execute('SELECT 1 FROM rooms WHERE id=?', (candidate,)).fetchone():
            suffix += 1
            candidate = '%s-%d' % (base, suffix)
        return candidate

    def room_create(self, actor, title, room=None):
        require(isinstance(title, str) and 0 < len(title.strip()) <= 80, 'room name required')
        with self.lock, self.db:
            require(self.db.execute('SELECT 1 FROM devices WHERE id=? AND active=1', (actor['id'],)).fetchone(), 'device revoked')
            identity = (room or '').strip() or self._room_slug(title)
            require(isinstance(identity, str) and 0 < len(identity) <= 64, 'invalid room identity')
            require(not self.db.execute('SELECT 1 FROM rooms WHERE id=?', (identity,)).fetchone(), 'room already exists')
            self.db.execute('INSERT INTO rooms VALUES(?,?)', (identity, title.strip()))
            self.db.execute('INSERT INTO grants VALUES(?,?)', (actor['id'], identity))
            return {'id': identity, 'title': title.strip()}

    def room_rename(self, actor, room, title):
        require(isinstance(title, str) and 0 < len(title.strip()) <= 80, 'room name required')
        with self.lock, self.db:
            self.access(actor, room)
            require(self.db.execute('SELECT 1 FROM rooms WHERE id=?', (room,)).fetchone(), 'room not found')
            self.db.execute('UPDATE rooms SET title=? WHERE id=?', (title.strip(), room))
            return {'id': room, 'title': title.strip()}

    def bind(self, actor, room, native, app, title, generation=1):
        require(app in ('codex-queue', 'opencode-bridge', 'claude-channel') + PULL_LIKE, 'unsupported adapter')
        require(isinstance(native, str) and 0 < len(native) <= 128, 'exact native session required')
        require(isinstance(title, str) and 0 < len(title) <= 200, 'conversation title required')
        if app == 'codex-queue':
            require(str(uuid.UUID(native)) == native, 'canonical Codex task UUID required')
        if app == 'opencode-bridge':
            require(native.startswith('ses_') and native.replace('_', '').isalnum(), 'OpenCode native session ID required')
        with self.lock, self.db:
            self.access(actor, room)
            row = self.db.execute('SELECT * FROM sessions WHERE device=? AND room=? AND app=? AND native=?', (actor['id'], room, app, native)).fetchone()
            if row:
                # A currently-inactive row means this exact session was
                # disconnected (session_remove), not merely superseded by a
                # newer live generation, so there is no concurrent stale
                # writer left to fence out. Only enforce the fence while the
                # previous binding is still active, so a removed session can
                # always reconnect rather than being stuck behind a
                # generation number from before it was removed.
                if row['active']:
                    require(generation >= row['generation'], 'stale connector generation')
                self.db.execute('UPDATE sessions SET generation=?,active=1,title=? WHERE id=?', (generation, title, row['id']))
                identity = row['id']
            else:
                identity = uid()
                self.db.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?,?,1)', (identity, actor['id'], room, native, app, title, generation))
            return dict(self.db.execute('SELECT * FROM sessions WHERE id=?', (identity,)).fetchone())

    def check_sender(self, actor, room, sender, generation):
        if not sender:
            return
        row = self.db.execute('SELECT * FROM sessions WHERE id=?', (sender,)).fetchone()
        require(row and row['room'] == room and row['device'] == actor['id'] and row['active'] and row['generation'] == generation, 'sender binding or generation invalid')

    def event(self, actor, event):
        require(event.get('version') == VERSION, 'unsupported protocol version')
        require(isinstance(event.get('id'), str) and len(event['id']) <= 128, 'stable event ID required')
        room, kind, body = event.get('room'), event.get('kind'), event.get('body')
        require(isinstance(body, dict) and len(encoded(body).encode('utf-8')) <= MAX_BODY, 'invalid or oversized event')
        require(kind in ('message', 'receipt', 'object'), 'unsupported event kind')
        sender = event.get('sender') or ''
        original_body = encoded(body)
        with self.lock, self.db:
            self.access(actor, room)
            self.check_sender(actor, room, sender, event.get('generation'))
            existing = self.db.execute('SELECT * FROM events WHERE id=?', (event['id'],)).fetchone()
            if existing:
                require(existing['device'] == actor['id'] and existing['room'] == room and existing['sender'] == sender and existing['kind'] == kind and existing['body'] == encoded(body), 'idempotency ID reused for different event')
                return self.decode(existing)
            if kind == 'message':
                require(isinstance(body.get('text'), str) and body['text'].strip(), 'message text required')
                targets = body.get('targets', [])
                require(isinstance(targets, list) and len(targets) <= 100 and len(set(targets)) == len(targets), 'invalid exact targets')
                require(not sender or sender not in targets, 'self-delivery is not allowed; post to the board instead')
                if targets:
                    pending = self.db.execute("SELECT count(*) FROM receipts r JOIN events e ON r.message=e.id WHERE e.room=? AND r.state IN ('waiting','pending')", (room,)).fetchone()[0]
                    require(pending+len(targets) <= MAX_QUEUE, 'room delivery queue full; resolve pending work first')
                if sender and targets:
                    recent = self.db.execute("SELECT count(*) FROM events WHERE sender=? AND kind='message' AND created>?", (sender, time.time()-60)).fetchone()[0]
                    require(recent < 12, 'agent message rate limit reached; pause and let the person respond')
                for target in targets:
                    row = self.db.execute('SELECT * FROM sessions WHERE id=? AND room=? AND active=1', (target, room)).fetchone()
                    require(row, 'target session is not active in this room')
                reply = body.get('reply_to')
                if reply:
                    require(self.db.execute('SELECT 1 FROM events WHERE id=? AND room=? AND kind=?', (reply, room, 'message')).fetchone(), 'reply source missing or in another room')
                for target in targets:
                    self.db.execute('INSERT INTO receipts(message,target,state,reason,updated) VALUES(?,?,?,?,?)', (event['id'], target, 'waiting', 'Waiting for device', time.time()))
            elif kind == 'receipt':
                target = body.get('target')
                require(sender == target, 'receipt requires exact receiving session')
                state = body.get('state')
                require(state in ('pending', 'submitted', 'acknowledged', 'unavailable', 'uncertain'), 'invalid receipt state')
                row = self.db.execute('SELECT * FROM receipts WHERE message=? AND target=?', (body.get('message'), target)).fetchone()
                require(row, 'receipt target does not belong to message')
                # Receipt updates may arrive out of order after reconnect. Never regress
                # explicit acknowledgement or a definitive/ambiguous native dispatch.
                revision=body.get('revision',row['revision']+1)
                require(isinstance(revision,int) and revision>=0,'invalid receipt revision')
                allowed = (row['state'] == 'waiting' or state == 'acknowledged' or (row['state'] == 'pending' and state != 'pending')
                           or (row['state']=='unavailable' and state=='pending' and body.get('recovered_unsent') is True))
                allowed = allowed and revision > row['revision'] and row['state']!='acknowledged'
                if allowed:
                    self.db.execute('UPDATE receipts SET state=?,reason=?,updated=?,revision=? WHERE message=? AND target=?', (state, str(body.get('reason', ''))[:300], time.time(), revision, body['message'], target))
            else:
                self.object_event(actor, room, sender, json.loads(original_body))
            self.db.execute('INSERT INTO events(id,room,device,sender,kind,body,created) VALUES(?,?,?,?,?,?,?)', (event['id'], room, actor['id'], sender, kind, original_body, time.time()))
            result = self.decode(self.db.execute('SELECT * FROM events WHERE id=?', (event['id'],)).fetchone())
            self.changed.notify_all()
            return result

    def object_event(self, actor, room, sender, body):
        identity, kind, data = body.get('id'), body.get('type'), body.get('data')
        require(isinstance(identity, str) and len(identity) <= 128 and isinstance(data, dict), 'object ID and data required')
        require(kind in ('plan', 'decision', 'work', 'review', 'claim'), 'unsupported collaboration object')
        old = self.db.execute('SELECT * FROM objects WHERE id=?', (identity,)).fetchone()
        require(not old or old['room'] == room and old['kind'] == kind, 'object room/type immutable')
        previous = json.loads(old['data']) if old else None
        require(body.get('version') == (old['version'] + 1 if old else 1), 'stale object version; refresh before editing')
        author = sender or actor['id']
        if kind == 'work':
            require(data.get('state') in STATES and data.get('title'), 'work title and valid state required')
            require(self.db.execute('SELECT 1 FROM sessions WHERE id=? AND room=?', (data.get('owner'), room)).fetchone(), 'work owner must be an exact room session')
            if previous:
                require(data.get('owner') == previous.get('owner'), 'create a new work request to reassign; preserve original ownership')
            if sender and data['state'] != 'proposed':
                require(sender == data['owner'], 'only assigned owner can advance work')
            if data['state'] == 'resolved':
                require(data.get('evidence'), 'completion evidence required')
        elif kind == 'review':
            require(data.get('artifact') and data.get('revision') and data.get('base'), 'immutable artifact, revision and base required')
            require(data.get('verdict') in ('pending', 'approved', 'changes requested'), 'review verdict required')
            require(self.db.execute('SELECT 1 FROM sessions WHERE id=? AND room=?', (data.get('reviewer'), room)).fetchone(), 'exact reviewer required')
            artifact_changed = previous and any(previous.get(k) != data.get(k) for k in ('revision', 'artifact', 'base'))
            if previous:
                require(data.get('reviewer') == previous.get('reviewer'), 'reviewer is immutable')
                if artifact_changed:
                    require(data['verdict'] == 'pending', 'changed artifact invalidates previous approval')
                    data['findings'] = ''
                elif sender != data['reviewer']:
                    require(all(data.get(k) == previous.get(k) for k in ('verdict', 'findings')),
                            'only exact reviewer can change verdict or findings')
            if data['verdict'] != 'pending':
                require(sender == data['reviewer'] or (previous and not artifact_changed and
                        all(data.get(k) == previous.get(k) for k in ('verdict', 'findings'))),
                        'only exact reviewer can give a verdict')
                require(data.get('checks') and data.get('findings') is not None, 'checks and findings required')
            data['self_review'] = data.get('reviewer') == (old['author'] if old else author)
        elif kind == 'decision':
            require(data.get('text') and data.get('state') in ('proposed', 'accepted', 'superseded'), 'decision text and state required')
            data.pop('accepted_by', None)
            data.pop('accepted_at', None)
            if data['state'] == 'accepted':
                data['accepted_by'] = author
                data['accepted_at'] = time.time()
        elif kind == 'plan':
            require(data.get('objective') and isinstance(data.get('steps'), list), 'objective and plan steps required')
        else:
            require(data.get('scope') and isinstance(data.get('expires'), (int, float)) and data['expires'] <= time.time()+86400, 'claim needs scope and bounded lease')
            if old:
                require(old['author'] == author, 'only claim owner may renew or release')
            conflicts = [r for r in self.db.execute('SELECT * FROM objects WHERE room=? AND kind=? AND id<>?', (room, 'claim', identity))
                         if json.loads(r['data']).get('scope') == data['scope'] and json.loads(r['data']).get('expires', 0) > time.time() and r['author'] != author]
            data['conflicts'] = [r['id'] for r in conflicts]
        self.db.execute('INSERT INTO objects VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET version=excluded.version,data=excluded.data', (identity, room, kind, body['version'], encoded(data), old['author'] if old else author))

    @staticmethod
    def decode(row):
        event = dict(row)
        event['body'] = json.loads(event['body'])
        event['version'] = VERSION
        return event

    def stream(self, actor, room, after=0, timeout=0):
        require(isinstance(after, int) and after >= 0, 'valid replay cursor required')
        deadline = time.monotonic()+min(25, max(0, timeout))
        with self.changed:
            while True:
                self.access(actor, room)
                rows = self.db.execute('SELECT * FROM events WHERE room=? AND seq>? ORDER BY seq LIMIT 200', (room, after)).fetchall()
                if rows or time.monotonic() >= deadline:
                    page, size = [], 0
                    for row in rows:
                        event = self.decode(row)
                        byte_count = len(encoded(event).encode('utf-8')) + 2
                        if page and size+byte_count > 1_000_000:
                            break
                        page.append(event)
                        size += byte_count
                    return page
                self.changed.wait(min(1, deadline-time.monotonic()))

    def snapshot(self, actor, room, cursor=None):
        cursor = cursor or {}
        require(isinstance(cursor, dict), 'invalid snapshot cursor')
        with self.lock:
            self.access(actor, room)
            queries = {
                'rooms': ('SELECT rooms.* FROM rooms JOIN grants ON rooms.id=grants.room WHERE grants.device=? ORDER BY rooms.id', (actor['id'],)),
                'sessions': ('SELECT s.*,d.name AS device_name FROM sessions s JOIN devices d ON s.device=d.id WHERE s.room=? ORDER BY s.id', (room,)),
                'devices': ('SELECT d.id,d.name,d.active,d.role FROM devices d JOIN grants g ON d.id=g.device WHERE g.room=? ORDER BY d.id', (room,)),
                'pairing': ('SELECT id,name,device,expires,approved FROM pairing WHERE room=? AND used=0 AND expires>? AND device IS NOT NULL ORDER BY id', (room,time.time())),
                'receipts': ('SELECT r.* FROM receipts r JOIN events e ON r.message=e.id WHERE e.room=? ORDER BY r.message,r.target', (room,)),
                'objects': ('SELECT * FROM objects WHERE room=? ORDER BY id', (room,)),
            }
            result, next_cursor, size, more = {}, {}, 0, False
            for name, (sql, args) in queries.items():
                offset = cursor.get(name, 0)
                require(isinstance(offset, int) and 0 <= offset <= 10_000_000, 'invalid snapshot offset')
                rows = self.rows(sql+' LIMIT 201 OFFSET ?', args+(offset,)) if name != 'pairing' or actor['role']=='admin' else []
                selected = []
                for row in rows[:200]:
                    if name == 'objects':row['data'] = json.loads(row['data'])
                    byte_count = len(encoded(row).encode('utf-8')) + 2
                    if size + byte_count > 1_000_000:break
                    selected.append(row)
                    size += byte_count
                result[name] = selected
                next_cursor[name] = offset + len(selected)
                more = more or len(rows) > len(selected)
            result['next'] = next_cursor if more else None
            return result
