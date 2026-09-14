"""Local bridge to the existing room during the staged desktop cutover.

Only explicitly bound sessions are forwarded. Existing host MCP connections
remain intact. This bridge is local-only and never exposed by the paired hub.
The old shared-token room is still a shared trust domain; it does not acquire
per-agent authentication by being displayed in the desktop app.
"""
import json
import re
import time
import urllib.parse
import urllib.request
from desktop.node import NoRedirect
from desktop.protocol import encoded, require


class Legacy:
    def __init__(self, node, port=8787):
        self.node = node
        self.url = 'http://127.0.0.1:%d' % int(port)
        self.session = 'desktop-' + node.get('device')
        self.agent = 'desktop@local'
        self.channel = 'general'
        with node.lock, node.db:
            node.db.execute('CREATE TABLE IF NOT EXISTS legacy_links(delivery TEXT PRIMARY KEY, message TEXT, target TEXT, request TEXT, legacy_message TEXT)')

    def call(self, path, data=None, timeout=5):
        token = self.node.vault.get('legacy-token') if self.node.get('legacy_requires_token') else ''
        request = urllib.request.Request(self.url+path, data=encoded(data).encode() if data is not None else None,
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer '+(token or '')})
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            return json.loads(response.read())

    def discover(self):
        return self.call('/api/sessions?channel=general')['sessions']

    def open(self):
        if self.node.get('legacy_cursor') is None:
            channels=self.call('/api/channels')['channels']
            latest=next((c['messages'] for c in channels if c['channel']==self.channel),0)
            self.node.put('legacy_cursor',latest)
        self.call('/api/join',{'agent':self.agent,'channel':self.channel,'role':'Desktop transport connector'})
        self.call('/api/register',{'session':self.session,'agent':self.agent,'channel':self.channel,'adapter':'pull'})

    def outbox(self):
        bindings=[b for b in self.node.bindings() if b.get('transport')=='local-room']
        if not bindings:return
        sessions={s['id']:s for s in self.discover()}
        if self.node.get('paused') or not self.node.online:return
        for binding in bindings:
            if binding.get('paused'):continue
            self.node.delivery.heartbeat(binding['id'],binding['room'])
            row=self.node.delivery.claim(binding['id'],binding['room'],binding['app'])
            if row:
                current=sessions.get(binding['legacy_session'])
                if not current or current['adapter']!=binding['app'] or (binding['app']=='codex-queue' and current['target']!=binding['native']):
                    self.node.delivery.finish(row['id'],'unavailable','Existing local session is disconnected or changed')
                    continue
                with self.node.lock,self.node.db:
                    self.node.db.execute('INSERT OR IGNORE INTO legacy_links VALUES(?,?,?,?,NULL)',(row['id'],row['message'],binding['id'],'desktop:'+row['message']+':'+binding['id']))
                self.node.delivery.finish(row['id'],'relaying','Waiting for the existing local room')
        # POST retries use v2's durable idempotency key, never a second native send.
        for link in self.node.rows('SELECT * FROM legacy_links'):
            binding=self.node.binding(link['target'])
            if not link['legacy_message']:
                source=self.node.source_message(binding['room'],link['message'])
                text=('Agent Room desktop message. Reply through your existing room tools to_session='+self.session+'. '
                      'Start your reply with [desktop-reply:'+link['message']+'] so it is linked in the desktop app. '
                      'Use your normal room_ack only after reading the complete native delivery.\n\n'+source['text'])
                result=self.call('/api/post',{'channel':self.channel,'from':self.agent,'from_session':self.session,
                    'to_session':binding['legacy_session'],'text':text,'request_id':link['request']})
                link['legacy_message']=result['posted']['id']
                with self.node.lock,self.node.db:
                    self.node.db.execute('UPDATE legacy_links SET legacy_message=? WHERE delivery=?',(link['legacy_message'],link['delivery']))
            rows=self.call('/api/delivery?'+urllib.parse.urlencode({'channel':self.channel,'message':link['legacy_message']}))['deliveries']
            remote=next((r for r in rows if r['session']==binding['legacy_session']),None)
            if remote and remote['state'] in ('submitted','acknowledged','uncertain','unavailable'):
                with self.node.delivery.lock,self.node.delivery.db:
                    self.node.delivery.db.execute("UPDATE deliveries SET state=?,reason=?,updated=? WHERE id=? AND state<>'acknowledged'",(remote['state'],remote['reason'],time.time(),link['delivery']))
        self.node.report()

    def receive(self, timeout=20):
        page=self.call('/api/wait?'+urllib.parse.urlencode({'channel':self.channel,'since':self.node.get('legacy_cursor',0),'timeout':timeout}),timeout=timeout+5)['messages']
        bindings={b['legacy_session']:b for b in self.node.bindings() if b.get('transport')=='local-room'}
        for message in page:
            binding=bindings.get(message.get('from_session'))
            if not binding or message.get('to_session')!=self.session:continue
            text=message['text']
            match=re.match(r'^\[desktop-reply:([^\]]+)\]\s*',text)
            reply=None
            if match:
                linked=self.node.rows('SELECT 1 FROM legacy_links WHERE message=? AND target=?',(match[1],binding['id']))
                if linked:reply=match[1];text=text[match.end():]
            self.node.enqueue('message',{'text':text,'targets':[],'reply_to':reply,'source_room_message':message['id']},binding['id'],event_id='local-room:'+message['id'])
        if page:self.node.put('legacy_cursor',page[-1]['seq'])

    def run(self):
        opened=False
        while not self.node.stop.is_set():
            try:
                if not any(b.get('transport')=='local-room' for b in self.node.bindings()):
                    self.node.stop.wait(2);continue
                if not opened:self.open();opened=True
                self.outbox()
                self.receive(2)
            except Exception:
                self.node.error='Existing local room connection unavailable. Queued messages are retained.'
                self.node.stop.wait(3)
