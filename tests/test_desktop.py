"""Focused v3 recovery, authorization and workflow checks. Synthetic devices only."""
import copy
import json
import os
import secrets
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer

from desktop.protocol import Hub, uid, encoded
from desktop.node import Node, Remote, hub_url
from desktop.secrets import MemoryVault
from desktop_main import handler


class HubTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hub = Hub(str(Path(self.tmp.name)/'hub.sqlite3'))
        self.secret = secrets.token_urlsafe(48)
        self.device = self.hub.bootstrap('Mac A', self.secret)
        self.actor = self.hub.auth(self.secret)

    def tearDown(self):
        self.hub.db.close()
        self.tmp.cleanup()

    def paired(self, room='general'):
        invitation = self.hub.pair_create(self.actor, room)
        identity, token = uid(), secrets.token_urlsafe(48)
        self.hub.pair_request(invitation['id'], invitation['proof'], 'Mac B', identity)
        self.hub.pair_approve(self.actor, invitation['id'])
        self.hub.pair_finish(invitation['id'], invitation['proof'], identity, token)
        return self.hub.auth(token), invitation, token

    def binding(self, actor=None, app='codex-queue', generation=1, native=None):
        return self.hub.bind(actor or self.actor, 'general', native or uid(), app, 'Synthetic conversation', generation)

    def message(self, sender='', targets=None, text='Synthetic message'):
        return {'version': 1, 'id': uid(), 'room': 'general', 'sender': sender, 'generation': 1,
                'kind': 'message', 'body': {'text': text, 'targets': targets or []}}

    def object(self, kind, data, identity=None, version=1, sender=''):
        event = self.message(sender)
        event.update(kind='object', body={'id': identity or uid(), 'type': kind, 'data': data, 'version': version})
        return event

    def test_pairing_requires_approval_expiry_and_single_redemption(self):
        invitation = self.hub.pair_create(self.actor, 'general')
        other, token = uid(), secrets.token_urlsafe(48)
        self.hub.pair_request(invitation['id'], invitation['proof'], 'Mac B', other)
        with self.assertRaises(ValueError):
            self.hub.pair_finish(invitation['id'], invitation['proof'], other, token)
        self.hub.pair_approve(self.actor, invitation['id'])
        self.hub.pair_finish(invitation['id'], invitation['proof'], other, token)
        self.hub.pair_finish(invitation['id'], invitation['proof'], other, token)  # dropped response safely reconciles
        with self.assertRaises(ValueError):
            self.hub.pair_finish(invitation['id'], invitation['proof'], other, secrets.token_urlsafe(48))
        exp = self.hub.pair_create(self.actor, 'general')
        self.hub.db.execute('UPDATE pairing SET expires=0 WHERE id=?', (exp['id'],))
        with self.assertRaises(ValueError):
            self.hub.pair_request(exp['id'], exp['proof'], 'late', uid())

    def test_device_scope_sender_spoof_and_revocation(self):
        other, _, token = self.paired()
        own = self.binding()
        with self.assertRaises(ValueError):
            self.hub.event(other, self.message(own['id']))
        with self.assertRaises(ValueError):
            self.hub.snapshot(other, 'private')
        with self.assertRaises(ValueError):
            self.hub.pair_create(other, 'general')
        self.hub.revoke(self.actor, other['id'], 'general')
        with self.assertRaises(ValueError):
            self.hub.auth(token)
        with self.assertRaises(ValueError):
            self.hub.snapshot(other, 'general')  # previously authenticated stream actor

    def test_pinned_exact_target_and_replay_conflicts(self):
        binding = self.binding()
        message = self.message(targets=[binding['id']])
        first = self.hub.event(self.actor, message)
        self.assertEqual(first['seq'], self.hub.event(self.actor, message)['seq'])
        changed = copy.deepcopy(message)
        changed['body']['text'] = 'changed content'
        with self.assertRaises(ValueError):
            self.hub.event(self.actor, changed)
        with self.assertRaises(ValueError):
            self.hub.event(self.actor, self.message(targets=['Synthetic conversation']))
        replacement = self.binding()
        self.assertNotEqual(binding['id'], replacement['id'])
        self.assertEqual([binding['id']], self.hub.stream(self.actor, 'general')[0]['body']['targets'])

    def test_generation_fence_and_native_identity_survives_reconnect(self):
        binding = self.binding()
        renewed = self.binding(native=binding['native'], generation=2)
        self.assertEqual(binding['id'], renewed['id'])
        with self.assertRaises(ValueError):
            self.hub.event(self.actor, self.message(binding['id']))
        with self.assertRaises(ValueError):
            self.binding(native=binding['native'], generation=1)
        message = self.message(binding['id'])
        message['generation'] = 2
        self.hub.event(self.actor, message)

    def test_receipt_requires_exact_recipient_and_never_regresses(self):
        recipient, wrong = self.binding(), self.binding()
        message = self.hub.event(self.actor, self.message(targets=[recipient['id']]))
        def receipt(sender, state):
            event = self.message(sender)
            event.update(kind='receipt', body={'message': message['id'], 'target': recipient['id'], 'state': state})
            return event
        with self.assertRaises(ValueError):
            self.hub.event(self.actor, receipt(wrong['id'], 'acknowledged'))
        self.hub.event(self.actor, receipt(recipient['id'], 'submitted'))
        self.assertEqual('submitted', self.hub.snapshot(self.actor, 'general')['receipts'][0]['state'])
        self.hub.event(self.actor, receipt(recipient['id'], 'acknowledged'))
        self.hub.event(self.actor, receipt(recipient['id'], 'pending'))
        self.assertEqual('acknowledged', self.hub.snapshot(self.actor, 'general')['receipts'][0]['state'])

    def test_stream_replay_wakes_and_duplicate_ids_are_atomic(self):
        result = []
        thread = threading.Thread(target=lambda: result.extend(self.hub.stream(self.actor, 'general', 0, 3)))
        thread.start()
        event = self.message()
        contenders = [threading.Thread(target=lambda: self.hub.event(self.actor, event)) for _ in range(6)]
        for t in contenders:t.start()
        for t in contenders:t.join()
        thread.join(4)
        self.assertEqual(1, len(result))
        self.assertEqual(1, len(self.hub.stream(self.actor, 'general')))
        self.assertEqual([], self.hub.stream(self.actor, 'general', result[0]['seq']))

    def test_work_acceptance_completion_and_no_implicit_delivery_receipt(self):
        owner = self.binding()
        request = self.object('work', {'title': 'Inspect fixture', 'owner': owner['id'], 'state': 'proposed'})
        self.hub.event(self.actor, request)
        complete = self.object('work', {'title': 'Inspect fixture', 'owner': owner['id'], 'state': 'resolved'}, request['body']['id'], 2, owner['id'])
        with self.assertRaises(ValueError):
            self.hub.event(self.actor, complete)
        complete['body']['data']['evidence'] = 'Fixture assertion passed'
        self.hub.event(self.actor, complete)
        self.assertEqual([], self.hub.snapshot(self.actor, 'general')['receipts'])
        with self.assertRaises(ValueError):
            self.hub.event(self.actor, self.object('work', complete['body']['data'], request['body']['id'], 2))

    def test_review_revision_invalidates_and_only_reviewer_can_approve(self):
        author, reviewer = self.binding(), self.binding()
        data = {'artifact': 'fixture.patch', 'revision': 'a'*40, 'base': 'b'*40, 'reviewer': reviewer['id'], 'verdict': 'pending'}
        packet = self.object('review', data, sender=author['id'])
        self.hub.event(self.actor, packet)
        approved = dict(data, verdict='approved', checks='fixture suite passed', findings=[])
        with self.assertRaises(ValueError):
            self.hub.event(self.actor, self.object('review', approved, packet['body']['id'], 2, author['id']))
        self.hub.event(self.actor, self.object('review', approved, packet['body']['id'], 2, reviewer['id']))
        changed = dict(approved, revision='c'*40)
        with self.assertRaises(ValueError):
            self.hub.event(self.actor, self.object('review', changed, packet['body']['id'], 3, reviewer['id']))
        changed['verdict'] = 'pending'
        self.hub.event(self.actor, self.object('review', changed, packet['body']['id'], 3, author['id']))
        self.assertEqual('pending', self.hub.snapshot(self.actor, 'general')['objects'][0]['data']['verdict'])

    def test_decision_provenance_retry_and_claim_conflicts(self):
        decision = self.object('decision', {'text': 'Use a durable outbox', 'state': 'accepted'})
        self.hub.event(self.actor, decision)
        self.hub.event(self.actor, decision)
        item = self.hub.snapshot(self.actor, 'general')['objects'][0]
        self.assertEqual(self.device, item['data']['accepted_by'])
        self.assertNotIn('accepted_by', decision['body']['data'])
        a, b = self.binding(), self.binding()
        for actor in (a,b):
            self.hub.event(self.actor, self.object('claim', {'scope': 'repo/fixture', 'expires': time.time()+60}, sender=actor['id']))
        claims = [o for o in self.hub.snapshot(self.actor,'general')['objects'] if o['kind']=='claim']
        self.assertEqual([0,1], sorted(len(c['data']['conflicts']) for c in claims))

    def test_future_schema_refused(self):
        path=Path(self.tmp.name)/'future.sqlite3'
        db=sqlite3.connect(path);db.execute('PRAGMA user_version=99');db.close()
        with self.assertRaises(ValueError):Hub(str(path))


class NodeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.vault=MemoryVault()
        self.node=Node(Path(self.tmp.name)/'A',self.vault,allow_loopback=True)
        self.node.setup('Synthetic Mac A')

    def tearDown(self):
        self.node.stop.set()
        self.node.db.close();self.node.delivery.db.close()
        if self.node.hub:self.node.hub.db.close()
        self.tmp.cleanup()

    def bind(self, app='codex-queue'):
        return self.node.bind({'native':'ses_fixture' if app=='opencode-bridge' else uid(),'app':app,'title':'Synthetic agent','directory':self.tmp.name})

    def test_local_outbox_restart_offline_and_idempotent_hub_resend(self):
        event=self.node.enqueue('message',{'text':'Durable fixture','targets':[]},event_id=uid())
        self.assertEqual('saved',event['state'])
        with patch.object(self.node,'call',side_effect=ConnectionError):
            with self.assertRaises(ConnectionError):self.node.sync_once()
        self.assertEqual('saved',self.node.snapshot()['outbox'][0]['state'])
        self.node.sync_once()
        self.node.db.execute("UPDATE outbox SET state='saved'");self.node.db.commit() # response lost after hub commit
        self.node.sync_once()
        self.assertEqual(1,len(self.node.snapshot()['events']))

    def test_cancel_before_send_and_no_recall_after_submission(self):
        queued=self.node.enqueue('message',{'text':'Cancel fixture','targets':[]})
        self.node.control('cancel',{'id':queued['id']})
        self.node.sync_once()
        self.assertEqual([],self.node.snapshot()['events'])
        second=self.node.enqueue('message',{'text':'Send fixture','targets':[]})
        self.node.sync_once()
        with self.assertRaises(ValueError):self.node.control('cancel',{'id':second['id']})

    def test_crash_after_cache_commit_reconciles_once(self):
        binding=self.bind()
        message=self.node.enqueue('message',{'text':'Synthetic inbound','targets':[binding['id']]})
        with patch.object(self.node,'route_cache',side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):self.node.sync_once()
        self.node.route_cache();self.node.route_cache()
        rows=self.node.delivery.status('general')
        self.assertEqual(1,len(rows));self.assertEqual(message['id'],rows[0]['message'])

    def test_bridge_lease_stale_send_uncertain_and_explicit_ack_reply(self):
        binding=self.bind('opencode-bridge')
        first=self.node.bridge_open(binding['id'],binding['native'],binding['app'])
        second=self.node.bridge_open(binding['id'],binding['native'],binding['app'])
        with self.assertRaises(ValueError):self.node.bridge_next(binding['id'],first['lease'],0)
        message=self.node.enqueue('message',{'text':'Read this synthetic fixture','targets':[binding['id']]})
        self.node.sync_once()
        with self.node.delivery.db:self.node.delivery.db.execute('UPDATE deliveries SET updated=0')
        item=self.node.bridge_next(binding['id'],second['lease'],0)
        self.node.bridge_sent(binding['id'],second['lease'],item['delivery']['id'],'submitted')
        self.node.report();self.node.sync_once()
        self.assertEqual('submitted',self.node.snapshot()['receipts'][0]['state'])
        self.node.tool(binding['id'],'room_ack',{'delivery_ids':[item['delivery']['id']]})
        self.node.tool(binding['id'],'room_post',{'text':'Read complete; fixture reply','reply_to':message['id']})
        self.node.report();self.node.sync_once()
        self.assertEqual('acknowledged',self.node.snapshot()['receipts'][0]['state'])
        self.assertEqual(2,len([e for e in self.node.snapshot()['events'] if e['kind']=='message']))
        self.assertIsNone(self.node.bridge_next(binding['id'],second['lease'],0)['delivery'])

    def test_old_connector_cannot_supersede_bridge_after_generation_change(self):
        binding=self.bind('claude-channel')
        old=self.node.bridge_open(binding['id'],binding['native'],binding['app'],binding['generation'])
        renewed=dict(binding,generation=binding['generation']+1)
        self.node.save_binding(renewed)
        fresh=self.node.bridge_open(binding['id'],binding['native'],binding['app'],renewed['generation'])
        with self.assertRaises(ValueError):
            self.node.control('bridge-open', {'binding':binding['id'],'native':binding['native'],
                                              'app':binding['app'],'expected_generation':binding['generation']})
        self.assertEqual(fresh['lease'],self.node.bridge_leases[binding['id']])
        with self.assertRaises(ValueError):self.node.bridge_next(binding['id'],old['lease'],0)
        self.assertIsNone(self.node.bridge_next(binding['id'],fresh['lease'],0)['delivery'])

    def test_pushed_ack_accepts_zero_optional_cursor_without_offered_page(self):
        binding = self.bind('opencode-bridge')
        message = self.node.enqueue('message', {'text': 'Complete push', 'targets': [binding['id']]})
        self.node.sync_once()
        opened = self.node.bridge_open(binding['id'], binding['native'], binding['app'])
        with self.node.delivery.db:
            self.node.delivery.db.execute('UPDATE deliveries SET updated=0')
        row = self.node.bridge_next(binding['id'], opened['lease'], 0)['delivery']
        request = {'binding': binding['id'], 'native': binding['native'],
                   'generation': opened['generation'], 'lease': opened['lease'],
                   'name': 'room_ack', 'args': {'delivery_ids': [row['id']], 'read_through': 0}}
        self.node.control('tool', request)
        self.assertEqual('acknowledged', self.node.delivery.status('general', message['id'])[0]['state'])
        self.assertEqual([], self.node.rows('SELECT * FROM offered'))
        request['args'] = {'delivery_ids': ['not-this-delivery'], 'read_through': 0}
        with self.assertRaises(ValueError):
            self.node.control('tool', request)
        request['args'] = {'delivery_ids': [row['id']], 'read_through': 1}
        with self.assertRaises(ValueError):
            self.node.control('tool', request)

    def test_bridge_reconnect_recovers_only_definitely_unsent_work(self):
        binding=self.bind('opencode-bridge')
        self.node.enqueue('message',{'text':'Waiting for the same session','targets':[binding['id']]})
        self.node.sync_once();self.node.report();self.node.sync_once()
        with self.node.delivery.db:self.node.delivery.db.execute('UPDATE sessions SET seen=0')
        self.node.delivery.expire_channels();self.node.report();self.node.sync_once()
        self.assertEqual('unavailable',self.node.snapshot()['receipts'][0]['state'])
        opened=self.node.bridge_open(binding['id'],binding['native'],binding['app'])
        self.node.report();self.node.sync_once()
        self.assertEqual('pending',self.node.snapshot()['receipts'][0]['state'])
        with self.node.delivery.db:self.node.delivery.db.execute('UPDATE deliveries SET updated=0')
        row=self.node.bridge_next(binding['id'],opened['lease'],0)['delivery']
        self.assertIsNotNone(row)
        self.node.bridge_sent(binding['id'],opened['lease'],row['id'],'uncertain')
        self.node.bridge_open(binding['id'],binding['native'],binding['app'])
        self.assertEqual('uncertain',self.node.delivery.status('general')[0]['state'])

    def test_complete_read_cursor_and_wrong_session_ack(self):
        first,second=self.bind(),self.bind()
        for i in range(3):self.node.enqueue('message',{'text':str(i)*25000,'targets':[first['id']]})
        self.node.sync_once()
        page=self.node.tool(first['id'],'room_read',{})
        self.assertEqual(1,len(page['messages']))
        with self.assertRaises(ValueError):self.node.tool(first['id'],'room_ack',{'read_through':999})
        with self.assertRaises(ValueError):self.node.tool(second['id'],'room_ack',{'delivery_ids':[page['deliveries'][0]['id']]})
        self.node.tool(first['id'],'room_ack',{'read_through':page['read_through']})
        self.assertNotEqual(page['messages'][0]['id'],self.node.tool(first['id'],'room_read',{})['messages'][0]['id'])

    def test_claude_app_pull_requires_exact_identity_offered_page_and_receiver_ack(self):
        binding=self.bind('pull')
        other=self.bind('pull')
        messages=[self.node.enqueue('message',{'text':str(i)*25000,'targets':[binding['id']]}) for i in range(2)]
        self.node.sync_once()
        self.assertTrue(all(row['state']=='unavailable' for row in self.node.delivery.status('general')))
        request={'binding':binding['id'],'native':binding['native'],'generation':binding['generation'],
                 'name':'room_read','args':{}}
        page=self.node.control('tool',request)
        self.assertEqual([messages[0]['id']],[event['id'] for event in page['messages']])
        self.assertEqual(2,len(page['deliveries']))
        self.assertTrue(all(row['state']=='unavailable' for row in self.node.delivery.status('general')))
        with self.assertRaises(ValueError):
            self.node.control('tool',dict(request,native=other['native']))
        with self.assertRaises(ValueError):
            self.node.control('tool',dict(request,generation=binding['generation']+1))
        ack=dict(request,name='room_ack',args={'delivery_ids':[page['deliveries'][0]['id']], 'read_through':page['read_through']})
        with self.assertRaises(ValueError):
            self.node.control('tool',dict(ack,binding=other['id'],native=other['native']))
        with self.assertRaises(ValueError):
            self.node.control('tool',dict(ack,args={'read_through':page['read_through']+1}))
        with self.assertRaises(ValueError):
            self.node.control('tool',dict(ack,args={'delivery_ids':[page['deliveries'][1]['id']]}))
        self.node.control('tool',ack)
        self.assertEqual('acknowledged',self.node.delivery.status('general',messages[0]['id'])[0]['state'])
        self.assertEqual('unavailable',self.node.delivery.status('general',messages[1]['id'])[0]['state'])
        self.assertEqual(messages[1]['id'],self.node.control('tool',request)['messages'][0]['id'])
        renewed=dict(binding,generation=binding['generation']+1)
        self.node.save_binding(renewed)
        with self.assertRaises(ValueError):self.node.control('tool',request)

    def test_claude_monitor_trigger_keeps_pull_receipt_and_generation_scoped(self):
        pull = self.bind('pull')
        channel = self.bind('claude-channel')
        watcher = {'binding': pull['id'], 'native': pull['native'], 'generation': pull['generation']}
        self.assertEqual({'oldest': 0, 'latest': 0}, self.node.control('watch-next', watcher))
        message = self.node.enqueue('message', {'text': 'A' * 25000, 'targets': [pull['id']]})
        second = self.node.enqueue('message', {'text': 'B' * 25000, 'targets': [pull['id']]})
        self.node.sync_once()
        status = self.node.control('watch-next', watcher)
        latest = status['latest']
        self.assertGreater(latest, 0)
        self.assertLess(status['oldest'], latest)
        self.assertEqual('unavailable', self.node.delivery.status('general', message['id'])[0]['state'])
        page = self.node.control('tool', dict(watcher, name='room_read', args={}))
        self.assertEqual([message['id']], [row['id'] for row in page['messages']])
        self.assertEqual(latest, self.node.control('watch-next', watcher)['latest'])
        for changed in (dict(watcher, native=channel['native']),
                        dict(watcher, generation=pull['generation'] + 1),
                        {'binding': channel['id'], 'native': channel['native'], 'generation': channel['generation']}):
            with self.assertRaises(ValueError):self.node.control('watch-next', changed)
        self.node.control('tool', dict(watcher, name='room_ack',
                           args={'delivery_ids': [self.node.delivery.status('general', message['id'])[0]['id']],
                                 'read_through': page['read_through']}))
        remaining = self.node.control('watch-next', watcher)
        self.assertEqual(latest, remaining['oldest'])
        self.assertEqual(latest, remaining['latest'])
        next_page = self.node.control('tool', dict(watcher, name='room_read', args={}))
        self.assertEqual([second['id']], [row['id'] for row in next_page['messages']])
        self.node.control('tool', dict(watcher, name='room_ack',
                           args={'delivery_ids': [self.node.delivery.status('general', second['id'])[0]['id']],
                                 'read_through': next_page['read_through']}))
        self.assertEqual({'oldest': 0, 'latest': 0}, self.node.control('watch-next', watcher))
        self.assertEqual('acknowledged', self.node.delivery.status('general', message['id'])[0]['state'])
        newer = dict(pull, generation=pull['generation'] + 1)
        self.node.save_binding(newer)
        with self.assertRaises(ValueError):self.node.control('watch-next', watcher)

    def test_real_http_protocol_scope_pair_two_synthetic_devices(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),handler(self.node,'not-used',True))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        other=Node(Path(self.tmp.name)/'B',MemoryVault(),allow_loopback=True)
        try:
            invitation=self.node.call('pair-create',{'room':'general'})
            url='http://127.0.0.1:%d'%server.server_port
            other.join_request(url,invitation['id'],invitation['proof'],'Synthetic Mac B')
            with self.assertRaises(ValueError):other.join_finish()
            self.node.call('pair-approve',{'id':invitation['id']})
            other.join_finish()
            binding=other.bind({'native':uid(),'app':'pull','title':'B fixture'})
            self.node.sync_once()
            message=self.node.enqueue('message',{'text':'A to B','targets':[binding['id']]})
            self.node.sync_once();other.sync_once()
            inbox=other.tool(binding['id'],'room_read',{})
            other.tool(binding['id'],'room_ack',{'delivery_ids':[inbox['deliveries'][0]['id']]})
            other.tool(binding['id'],'room_post',{'text':'B to A reply','reply_to':message['id']})
            other.report();other.sync_once();self.node.sync_once()
            self.assertEqual('acknowledged',self.node.snapshot()['receipts'][0]['state'])
            self.assertTrue(any(e['body'].get('text')=='B to A reply' for e in self.node.snapshot()['events']))
            with self.assertRaises(ValueError):Remote(url,'x'*48,True).call('snapshot',{})
        finally:
            other.db.close();other.delivery.db.close();server.shutdown();server.server_close()

    def test_transport_refuses_remote_plaintext_url_credentials_and_redirects(self):
        for url in ('http://example.org','https://user:password@example.org','https://example.org/?token=secret','file:///tmp/hub'):
            with self.assertRaises(ValueError):hub_url(url)
        self.assertEqual('https://example.org',hub_url('https://example.org/'))

    def test_unicode_event_and_snapshot_pages_fit_actual_http_byte_limit(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),handler(self.node,'',True))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        remote=Remote('http://127.0.0.1:%d'%server.server_port,self.vault.get('device'),True)
        try:
            for i in range(20):
                remote.call('event',{'version':1,'id':uid(),'room':'general','kind':'object','body':{'id':uid(),'version':1,'type':'decision','data':{'text':'界'*40000,'state':'proposed'}}})
            cursor,count=0,0
            while True:
                page=remote.call('events',{'room':'general','after':cursor})
                self.assertLess(len(encoded(page).encode()),1_010_000)
                if not page['events']:break
                count+=len(page['events']);cursor=page['events'][-1]['seq']
            self.assertEqual(20,count)
            cursor,count=None,0
            while True:
                page=remote.call('snapshot',{'room':'general','cursor':cursor})
                self.assertLess(len(encoded(page).encode()),1_010_000)
                count+=len(page['objects']);cursor=page['next']
                if not cursor:break
            self.assertEqual(20,count)
        finally:server.shutdown();server.server_close()


if __name__=='__main__':unittest.main()


class RequestTests(NodeTests):
    def test_connect_request_pending_then_approved_binds_exact_session(self):
        result = self.node.request_create('ses_newcomer', 'opencode-bridge', 'New synthetic session', self.tmp.name)
        self.assertEqual('pending', result['state'])
        snap = self.node.snapshot()
        self.assertEqual(1, len(snap['requests']))
        self.assertEqual('ses_newcomer', snap['requests'][0]['native'])
        decided = self.node.request_decide('ses_newcomer', 'opencode-bridge', True)
        self.assertEqual('approved', decided['state'])
        snap = self.node.snapshot()
        self.assertEqual(0, len(snap['requests']))
        binding = next(b for b in snap['bindings'] if b['native'] == 'ses_newcomer')
        self.assertEqual('New synthetic session', binding['title'])
        # Already-connected sessions report instead of re-requesting.
        again = self.node.request_create('ses_newcomer', 'opencode-bridge', 'New synthetic session', self.tmp.name)
        self.assertEqual('already-connected', again['state'])

    def test_connect_request_rejected_never_binds(self):
        self.node.request_create(uid(), 'codex-queue', 'Rejected synthetic task')
        with self.assertRaises(ValueError):
            self.node.request_decide('missing', 'codex-queue', True)
        rows = self.node.rows("SELECT native FROM requests WHERE state='pending'")
        native = rows[0]['native']
        decided = self.node.request_decide(native, 'codex-queue', False)
        self.assertEqual('rejected', decided['state'])
        snap = self.node.snapshot()
        self.assertEqual(0, len(snap['requests']))
        self.assertFalse(any(b['native'] == native for b in snap['bindings']))

    def test_opencode_request_requires_real_directory(self):
        with self.assertRaises(ValueError):
            self.node.request_create('ses_dirless', 'opencode-bridge', 'No directory', '/nonexistent-path')

    def test_request_model_round_trips_through_snapshot_and_approval(self):
        result = self.node.request_create('ses_modeled', 'opencode-bridge', 'Modeled session', self.tmp.name, 'glm-5-3')
        self.assertEqual('pending', result['state'])
        snap = self.node.snapshot()
        pending = next(r for r in snap['requests'] if r['native'] == 'ses_modeled')
        self.assertEqual('glm-5-3', pending['model'])
        decided = self.node.request_decide('ses_modeled', 'opencode-bridge', True)
        self.assertEqual('approved', decided['state'])
        snap = self.node.snapshot()
        binding = next(b for b in snap['bindings'] if b['native'] == 'ses_modeled')
        self.assertEqual('glm-5-3', binding['model'])

    def test_request_and_binding_without_model_stay_backward_compatible(self):
        result = self.node.request_create(uid(), 'codex-queue', 'No model synthetic task')
        self.assertEqual('pending', result['state'])
        snap = self.node.snapshot()
        pending = next(r for r in snap['requests'] if r['title'] == 'No model synthetic task')
        self.assertEqual('', pending['model'])
        decided = self.node.request_decide(pending['native'], 'codex-queue', True)
        self.assertEqual('approved', decided['state'])
        snap = self.node.snapshot()
        binding = next(b for b in snap['bindings'] if b['native'] == pending['native'])
        self.assertEqual('', binding['model'])
        # A binding created directly (not through the request flow) also defaults cleanly.
        direct = self.bind('claude-channel')
        self.assertEqual('', direct['model'])
