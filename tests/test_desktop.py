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

    def test_session_remove_settles_receipts_keeps_work_owner_resolvable_and_allows_reconnect(self):
        """Regression for M1. session_remove used to hard-delete the sessions
        row, which left any receipt still addressed to it stuck forever (no
        session will ever again report on its behalf) and made a work/review
        object it owns permanently un-updatable ('work owner must be an
        exact room session' can never again pass). Fix: soft-deactivate like
        revoke() and settle the session's own dangling receipts."""
        owner = self.binding(generation=3)
        message = self.hub.event(self.actor, self.message(targets=[owner['id']]))
        self.assertEqual('waiting', self.hub.snapshot(self.actor, 'general')['receipts'][0]['state'])
        request = self.object('work', {'title': 'Fixture task', 'owner': owner['id'], 'state': 'proposed'})
        self.hub.event(self.actor, request)
        self.assertEqual({'removed': False}, self.hub.session_remove(self.actor, 'general', 'never-existed'))
        self.assertEqual({'removed': True}, self.hub.session_remove(self.actor, 'general', owner['id']))
        # Idempotent: removing an already-inactive session is a no-op, not an error.
        self.assertEqual({'removed': False}, self.hub.session_remove(self.actor, 'general', owner['id']))
        # The row survives (inactive), so it stays a valid session reference...
        row = self.hub.db.execute('SELECT * FROM sessions WHERE id=?', (owner['id'],)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(0, row['active'])
        # ...the dangling receipt no longer sits in a permanently unresolvable
        # 'waiting' state (no session will ever report on the removed
        # session's behalf again)...
        receipt = self.hub.snapshot(self.actor, 'general')['receipts'][0]
        self.assertEqual('unavailable', receipt['state'])
        self.assertEqual('session removed', receipt['reason'])
        # ...and the work object it owns can still be updated/cancelled --
        # not permanently stuck -- because the owner session still resolves.
        cancel = self.object('work', {'title': 'Fixture task', 'owner': owner['id'], 'state': 'cancelled'}, request['body']['id'], 2)
        self.hub.event(self.actor, cancel)
        self.assertEqual('cancelled', self.hub.snapshot(self.actor, 'general')['objects'][0]['data']['state'])
        # A removed session is not permanently exiled: reconnecting the same
        # native+app pair must not be blocked by the generation number it
        # held before removal (there is no live writer left to fence out).
        reconnected = self.binding(native=owner['native'], generation=1)
        self.assertEqual(owner['id'], reconnected['id'])
        self.assertEqual(1, reconnected['generation'])

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

    def test_room_create_grants_creator_lists_alongside_general_and_renames(self):
        created = self.hub.room_create(self.actor, 'Feature Room')
        self.assertTrue(created['id'])
        self.assertEqual('Feature Room', created['title'])
        rooms = self.hub.snapshot(self.actor, 'general')['rooms']
        self.assertEqual({'general', created['id']}, {r['id'] for r in rooms})
        other, _, _ = self.paired()
        with self.assertRaises(ValueError):
            self.hub.access(other, created['id'])
        self.hub.room_rename(self.actor, created['id'], 'Renamed')
        rooms = self.hub.snapshot(self.actor, 'general')['rooms']
        self.assertEqual('Renamed', next(r['title'] for r in rooms if r['id'] == created['id']))
        with self.assertRaises(ValueError):
            self.hub.room_rename(self.actor, 'does-not-exist', 'X')

    def test_room_create_dedupes_slug_for_repeated_names(self):
        a = self.hub.room_create(self.actor, 'Same Name')
        b = self.hub.room_create(self.actor, 'Same Name')
        self.assertNotEqual(a['id'], b['id'])


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

    def test_wait_next_wakes_on_board_post_but_never_on_own_post(self):
        mine = self.bind('mcp')
        other = self.bind('mcp')
        watcher = {'binding': mine['id'], 'native': mine['native'], 'generation': mine['generation'], 'timeout': 0}
        self.assertEqual({'ready': False, 'seq': 0}, self.node.control('wait-next', watcher))
        # A board post (targets=[]) from another agent must wake wait-next even
        # though nothing addressed `mine` directly.
        self.node.tool(other['id'], 'room_post', {'text': 'Board question for anyone'})
        self.node.sync_once()
        status = self.node.control('wait-next', watcher)
        self.assertTrue(status['ready'])
        self.assertGreater(status['seq'], 0)
        # Reading and acknowledging through that seq resets readiness.
        page = self.node.control('tool', dict(watcher, name='room_read', args={}))
        self.node.control('tool', dict(watcher, name='room_ack', args={'read_through': page['read_through']}))
        self.assertEqual({'ready': False, 'seq': page['read_through']}, self.node.control('wait-next', watcher))
        # This binding's own post never wakes its own wait-next.
        self.node.tool(mine['id'], 'room_post', {'text': 'My own board post'})
        self.node.sync_once()
        mine_status = self.node.control('wait-next', watcher)
        self.assertFalse(mine_status['ready'])
        # ...but it does wake the other bound session, which did not send it.
        other_watcher = {'binding': other['id'], 'native': other['native'], 'generation': other['generation'], 'timeout': 0}
        self.assertTrue(self.node.control('wait-next', other_watcher)['ready'])

    def test_wait_next_wakes_on_targeted_and_human_message_and_times_out_cleanly(self):
        binding = self.bind('mcp')
        watcher = {'binding': binding['id'], 'native': binding['native'], 'generation': binding['generation']}
        started = time.monotonic()
        self.assertEqual({'ready': False, 'seq': 0}, self.node.control('wait-next', dict(watcher, timeout=0.2)))
        self.assertGreaterEqual(time.monotonic() - started, 0.15)
        self.node.enqueue('message', {'text': 'Human message, no sender', 'targets': []})
        self.node.sync_once()
        self.assertTrue(self.node.control('wait-next', dict(watcher, timeout=0))['ready'])
        with self.assertRaises(ValueError):
            self.node.control('wait-next', dict(watcher, timeout=0, generation=binding['generation'] + 1))

    def test_wait_next_woken_promptly_by_bridge_condition_notify(self):
        """A blocking wait-next call must be released as soon as route_cache
        notifies bridge_condition -- not only when its own poll loop happens
        to re-check -- so a resident loop is not left to sleep out its full
        hop even though route_cache already ran."""
        binding = self.bind('mcp')
        other = self.bind('mcp')
        watcher = {'binding': binding['id'], 'native': binding['native'], 'generation': binding['generation'], 'timeout': 15}
        result = {}
        def waiter():
            result['status'] = self.node.control('wait-next', watcher)
        thread = threading.Thread(target=waiter)
        started = time.monotonic()
        thread.start()
        time.sleep(0.2)  # let the waiter block on bridge_condition
        self.node.tool(other['id'], 'room_post', {'text': 'Wake up'})
        self.node.sync_once()
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 5, 'wait-next should wake immediately on notify, not sleep out the full hop')
        self.assertTrue(result['status']['ready'])

    def test_board_fanout_reports_stay_local_and_old_failures_are_retired(self):
        binding = self.bind('pull')
        board = self.node.enqueue('message', {'text': 'Board', 'targets': []})
        self.node.sync_once()
        delivery = self.node.delivery.status('general')[0]
        old = self.node.enqueue('receipt', {'message': board['id'], 'target': binding['id'],
                               'state': 'unavailable'}, binding['id'])
        with self.node.db:
            self.node.db.execute("UPDATE outbox SET state='failed',error='receipt target does not belong to message' WHERE id=?", (old['id'],))
        self.node.report()
        self.node.sync_once()
        self.assertEqual([], self.node.snapshot()['outbox'])
        self.assertEqual([], self.node.snapshot()['receipts'])
        self.node.tool(binding['id'], 'room_read', {})
        self.node.tool(binding['id'], 'room_ack', {'delivery_ids': [delivery['id']]})
        self.node.report(); self.node.sync_once()
        self.assertEqual('acknowledged', self.node.delivery.status('general')[0]['state'])
        self.assertEqual([], self.node.snapshot()['outbox'])
        self.assertEqual([], self.node.snapshot()['receipts'])

    def test_receipt_cleanup_preserves_explicit_and_unknown_failures(self):
        binding = self.bind('pull')
        message = self.node.enqueue('message', {'text': 'Direct', 'targets': [binding['id']]})
        self.node.sync_once()
        for source in [message['id'], 'unknown-source']:
            receipt = self.node.enqueue('receipt', {'message': source, 'target': binding['id'],
                                        'state': 'unavailable'}, binding['id'])
            with self.node.db:
                self.node.db.execute("UPDATE outbox SET state='failed',error='unrelated failure' WHERE id=?", (receipt['id'],))
        self.node.settle_board_reports()
        self.assertEqual(2, len(self.node.rows("SELECT id FROM outbox WHERE state='failed'")))

    def test_outbox_status_reports_confirmed_and_rejected_object_saves(self):
        binding = self.bind('pull')
        data = {'id': uid(), 'type': 'work', 'version': 1,
                'data': {'title': 'Work', 'owner': binding['id'], 'state': 'resolved'}}
        bad = self.node.control('object', data)
        self.assertEqual('saved', self.node.control('outbox-status', {'id': bad['id']})['state'])
        self.node.sync_once()
        result = self.node.control('outbox-status', {'id': bad['id']})
        self.assertEqual('failed', result['state'])
        self.assertIn('completion evidence', result['reason'])
        data['data']['evidence'] = 'Tests passed'
        good = self.node.control('object', data)
        self.node.sync_once()
        self.assertEqual('sent', self.node.control('outbox-status', {'id': good['id']})['state'])
        with self.assertRaises(ValueError):
            self.node.control('outbox-status', {'id': 'missing'})

    def test_board_post_fans_out_delivery_rows_to_room_members_not_sender(self):
        sender = self.bind('mcp')
        codex_recipient = self.bind('codex-queue')
        pull_recipient = self.bind('pull')
        self.node.tool(sender['id'], 'room_post', {'text': 'Board post fixture'})
        self.node.sync_once()
        rows = self.node.delivery.status('general')
        sessions = {row['session']: row['state'] for row in rows}
        self.assertNotIn(sender['id'], sessions)
        self.assertEqual('pending', sessions[codex_recipient['id']])
        self.assertEqual('unavailable', sessions[pull_recipient['id']])
        # Targeted delivery is unaffected: only the addressed session gets a row.
        self.node.tool(sender['id'], 'room_post', {'text': 'Targeted fixture', 'to_session': codex_recipient['id']})
        self.node.sync_once()
        targeted = [r for r in self.node.delivery.status('general') if r['message'] not in {row['message'] for row in rows}]
        self.assertEqual([codex_recipient['id']], [r['session'] for r in targeted])

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

    def test_generic_mcp_request_approve_binding_and_pull_like_treatment(self):
        result = self.node.request_create('native-mcp-1', 'mcp', 'Generic agent session', model='some-model-x')
        self.assertEqual('pending', result['state'])
        snap = self.node.snapshot()
        pending = next(r for r in snap['requests'] if r['native'] == 'native-mcp-1')
        self.assertEqual('some-model-x', pending['model'])
        decided = self.node.request_decide('native-mcp-1', 'mcp', True)
        self.assertEqual('approved', decided['state'])
        snap = self.node.snapshot()
        self.assertEqual(0, len(snap['requests']))
        binding = next(b for b in snap['bindings'] if b['native'] == 'native-mcp-1')
        self.assertEqual('mcp', binding['app'])
        self.assertEqual('some-model-x', binding['model'])
        # Read-on-demand, not push: routing marks it unavailable like a pull binding,
        # never pending, and dispatch_one never claims it for delivery.
        message = self.node.enqueue('message', {'text': 'Synthetic generic fixture', 'targets': [binding['id']]})
        self.node.sync_once()
        self.assertEqual('unavailable', self.node.delivery.status('general')[0]['state'])
        self.assertIsNone(self.node.delivery.claim())
        request = {'binding': binding['id'], 'native': binding['native'], 'generation': binding['generation'],
                   'name': 'room_read', 'args': {}}
        page = self.node.control('tool', request)
        self.assertEqual([message['id']], [event['id'] for event in page['messages']])
        # Same watch-next primitive as pull: no push, optional idle-wake polling only.
        watcher = {'binding': binding['id'], 'native': binding['native'], 'generation': binding['generation']}
        status = self.node.control('watch-next', watcher)
        self.assertGreater(status['latest'], 0)
        ack = dict(request, name='room_ack',
                   args={'delivery_ids': [page['deliveries'][0]['id']], 'read_through': page['read_through']})
        self.node.control('tool', ack)
        self.assertEqual('acknowledged', self.node.delivery.status('general')[0]['state'])

    def test_unknown_app_string_rejected_by_request_create_and_bind(self):
        with self.assertRaises(ValueError):
            self.node.request_create(uid(), 'random', 'Bad app synthetic session')
        with self.assertRaises(ValueError):
            self.node.bind({'native': uid(), 'app': 'random', 'title': 'Bad app synthetic session'})


class RoomTests(NodeTests):
    """Multi-room: 'general' stays the default and existing single-room installs
    keep working; a new room is a fully separate content scope."""

    def test_default_general_path_untouched_when_no_room_ever_created(self):
        snap = self.node.snapshot()
        self.assertEqual('general', snap['room'])
        self.assertEqual('general', snap['activeRoom'])
        self.assertIn('general', [r['id'] for r in snap['rooms']])
        binding = self.bind()
        self.assertEqual('general', binding['room'])

    def test_room_create_switches_active_room_and_binding_attaches_to_it(self):
        created = self.node.control('room-create', {'title': 'Build slice'})
        self.assertEqual(created['id'], self.node.get('room'))
        self.assertNotEqual('general', created['id'])
        binding = self.bind()
        self.assertEqual(created['id'], binding['room'])

    def test_switching_rooms_scopes_snapshot_messages(self):
        self.node.enqueue('message', {'text': 'General only', 'targets': []})
        created = self.node.control('room-create', {'title': 'Build slice'})
        self.node.enqueue('message', {'text': 'New room only', 'targets': []})
        self.node.sync_once()
        texts = [e['body']['text'] for e in self.node.snapshot()['events'] if e['kind'] == 'message']
        self.assertEqual(['New room only'], texts)
        self.node.control('room-select', {'room': 'general'})
        self.node.sync_once()
        texts = [e['body']['text'] for e in self.node.snapshot()['events'] if e['kind'] == 'message']
        self.assertEqual(['General only'], texts)

    def test_agent_post_and_workflow_object_go_to_the_binding_room_not_active_room(self):
        created = self.node.control('room-create', {'title': 'Build slice'})
        binding = self.bind()
        self.node.control('room-select', {'room': 'general'})
        # The bound agent posts and files work while the human has since
        # navigated back to General; its content must still land in its own room.
        self.node.tool(binding['id'], 'room_post', {'text': 'Still in my own room'})
        self.node.sync_once()
        general_texts = [e['body']['text'] for e in self.node.snapshot()['events'] if e['kind'] == 'message']
        self.assertEqual([], general_texts)
        self.node.control('room-select', {'room': created['id']})
        self.node.sync_once()
        own_texts = [e['body']['text'] for e in self.node.snapshot()['events'] if e['kind'] == 'message']
        self.assertEqual(['Still in my own room'], own_texts)

    def test_request_created_in_active_room_binds_into_it_even_after_switching_away(self):
        created = self.node.control('room-create', {'title': 'Feature branch'})
        result = self.node.request_create(uid(), 'codex-queue', 'Room-scoped synthetic task')
        self.assertEqual('pending', result['state'])
        self.node.control('room-select', {'room': 'general'})
        pending = next(r for r in self.node.snapshot()['requests'] if r['title'] == 'Room-scoped synthetic task')
        self.assertEqual(created['id'], pending['room'])
        decided = self.node.request_decide(pending['native'], 'codex-queue', True)
        self.assertEqual('approved', decided['state'])
        binding = next(b for b in self.node.snapshot()['bindings'] if b['native'] == pending['native'])
        self.assertEqual(created['id'], binding['room'])

    def test_room_rename_updates_title_everywhere_it_is_listed(self):
        created = self.node.control('room-create', {'title': 'Old name'})
        self.node.control('room-rename', {'room': created['id'], 'title': 'New name'})
        self.node.sync_once()
        rooms = self.node.snapshot()['rooms']
        self.assertEqual('New name', next(r['title'] for r in rooms if r['id'] == created['id']))

    def test_bind_refuses_the_same_native_app_into_a_different_room(self):
        """Regression for H2: binding an already-bound (native, app) pair into
        a second room used to succeed silently -- creating a second hub
        session and a second local binding for the same conversation -- which
        left mcp.py's resolve_binding() seeing two matches and locking the
        helper out entirely."""
        first = self.bind()
        other_room = self.node.control('room-create', {'title': 'Second room'})
        with self.assertRaises(ValueError):
            self.node.bind({'native': first['native'], 'app': first['app'],
                             'title': 'Second attempt', 'room': other_room['id']})
        bindings = [b for b in self.node.snapshot()['bindings'] if b['native'] == first['native']]
        self.assertEqual(1, len(bindings))
        self.assertEqual('general', bindings[0]['room'])
        # Re-binding into its own existing room (a reconnect/refresh) is unaffected.
        self.node.bind({'native': first['native'], 'app': first['app'],
                         'title': 'Same room reconnect', 'room': 'general'})
        bindings = [b for b in self.node.snapshot()['bindings'] if b['native'] == first['native']]
        self.assertEqual(1, len(bindings))

    def test_room_select_requires_a_grant_and_rejects_when_missing(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler(self.node, 'not-used', True))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        other = Node(Path(self.tmp.name)/'B', MemoryVault(), allow_loopback=True)
        try:
            invitation = self.node.call('pair-create', {'room': 'general'})
            url = 'http://127.0.0.1:%d' % server.server_port
            other.join_request(url, invitation['id'], invitation['proof'], 'Synthetic Mac B')
            self.node.call('pair-approve', {'id': invitation['id']})
            other.join_finish()
            created = self.node.control('room-create', {'title': 'A private slice'})
            with self.assertRaises(ValueError):
                other.control('room-select', {'room': created['id']})
            self.assertEqual({'room': 'general'}, other.control('room-select', {'room': 'general'}))
        finally:
            other.db.close();other.delivery.db.close();server.shutdown();server.server_close()


class PresenceAndRemovalTests(NodeTests):
    """Self-reported presence (Feature A) and disconnect/remove (Feature B)."""

    def test_binding_state_round_trips_defaults_unknown_and_rejects_invalid(self):
        binding = self.bind()
        snap = self.node.snapshot()
        self.assertEqual('unknown', next(b for b in snap['bindings'] if b['id'] == binding['id'])['state'])
        self.node.control('binding-state', {'binding': binding['id'], 'state': 'working'})
        snap = self.node.snapshot()
        self.assertEqual('working', next(b for b in snap['bindings'] if b['id'] == binding['id'])['state'])
        with self.assertRaises(ValueError):
            self.node.control('binding-state', {'binding': binding['id'], 'state': 'nonsense'})
        # Also addressable by native+app, like bind() itself.
        self.node.control('binding-state', {'native': binding['native'], 'app': binding['app'], 'state': 'blocked'})
        snap = self.node.snapshot()
        self.assertEqual('blocked', next(b for b in snap['bindings'] if b['id'] == binding['id'])['state'])
        with self.assertRaises(ValueError):
            self.node.control('binding-state', {'binding': 'does-not-exist', 'state': 'working'})

    def test_room_status_mcp_tool_sets_the_calling_sessions_state(self):
        binding = self.bind()
        result = self.node.tool(binding['id'], 'room_status', {'state': 'blocked'})
        self.assertEqual({'id': binding['id'], 'state': 'blocked'}, result)
        snap = self.node.snapshot()
        self.assertEqual('blocked', next(b for b in snap['bindings'] if b['id'] == binding['id'])['state'])
        with self.assertRaises(ValueError):
            self.node.tool(binding['id'], 'room_status', {'state': 'nope'})
        # Also reachable through the generic 'tool' control action the MCP layer uses.
        request = {'binding': binding['id'], 'native': binding['native'], 'generation': binding['generation'],
                   'name': 'room_status', 'args': {'state': 'done'}}
        self.node.control('tool', request)
        self.assertEqual('done', next(b for b in self.node.snapshot()['bindings'] if b['id'] == binding['id'])['state'])

    def test_binding_remove_deactivates_hub_session_settles_receipt_idempotently(self):
        """Regression for M1. The hub session row used to be hard-deleted on
        removal, which stranded any receipt still addressed to it (nothing
        will ever again report on the removed session's behalf) and would
        have made an owned work/review object permanently un-updatable. It
        must instead be soft-deactivated -- like revoke() -- and its
        dangling receipts settled, so no ghost receipt or stuck object is
        left behind."""
        keep = self.bind()
        gone = self.bind()
        self.node.enqueue('message', {'text': 'to be orphaned', 'targets': [gone['id']]})
        self.node.sync_once()
        self.assertIn(gone['id'], [r['id'] for r in self.node.hub.rows('SELECT id FROM sessions')])
        self.assertEqual('waiting', self.node.hub.rows('SELECT * FROM receipts WHERE target=?', (gone['id'],))[0]['state'])
        self.assertEqual(1, len(self.node.delivery.status('general')))
        result = self.node.control('binding-remove', {'binding': gone['id']})
        self.assertEqual({'removed': True, 'id': gone['id']}, result)
        snap = self.node.snapshot()
        remaining_ids = [b['id'] for b in snap['bindings']]
        self.assertNotIn(gone['id'], remaining_ids)
        self.assertIn(keep['id'], remaining_ids)
        # Hub session row is deactivated, not deleted: it stays a resolvable
        # session reference (e.g. for a work object it owns) instead of
        # being stranded.
        hub_session = next(r for r in self.node.hub.rows('SELECT * FROM sessions') if r['id'] == gone['id'])
        self.assertEqual(0, hub_session['active'])
        # No ghost receipt: the dangling receipt is settled rather than left
        # stuck in 'waiting' forever.
        receipt = self.node.hub.rows('SELECT * FROM receipts WHERE target=?', (gone['id'],))[0]
        self.assertEqual('unavailable', receipt['state'])
        self.assertEqual('session removed', receipt['reason'])
        # Local bookkeeping (offered cursor + delivery rows) cleaned up; no orphans.
        self.assertEqual([], self.node.rows('SELECT * FROM offered WHERE binding=?', (gone['id'],)))
        self.assertEqual([], [r for r in self.node.delivery.status('general') if r['session'] == gone['id']])
        # Idempotent: removing again, or removing something never bound, is a no-op.
        self.assertEqual({'removed': False}, self.node.control('binding-remove', {'binding': gone['id']}))
        self.assertEqual({'removed': False}, self.node.control('binding-remove', {'binding': 'never-existed'}))
        self.assertEqual({'removed': False}, self.node.control('binding-remove', {'native': 'nope', 'app': 'codex-queue'}))
        # The other binding is completely unaffected.
        self.assertEqual('unknown', next(b for b in self.node.snapshot()['bindings'] if b['id'] == keep['id'])['state'])

    def test_binding_remove_by_native_and_app_and_hub_removal_is_scoped_to_owning_device(self):
        binding = self.bind()
        result = self.node.control('binding-remove', {'native': binding['native'], 'app': binding['app']})
        self.assertEqual({'removed': True, 'id': binding['id']}, result)
        self.assertNotIn(binding['id'], [b['id'] for b in self.node.snapshot()['bindings']])

    def test_report_survives_and_cleans_an_orphan_delivery_from_a_remove_race(self):
        """Regression for H1. If a route_cache() pass reads a bindings
        snapshot just before binding_remove() deletes that binding, its
        delivery.route() call can land after forget() already ran, inserting
        a fresh delivery row for a session with no binding behind it. Before
        the fix, report() then raised on every single cycle (enqueue()
        requires a real binding to attribute the receipt to), which
        send_loop caught by marking the whole device permanently offline with
        no recovery path. report() must instead recognize and discard the
        orphan, and go on reporting for every binding that is still real."""
        keep = self.bind()
        gone = self.bind()
        self.node.control('binding-remove', {'binding': gone['id']})
        self.assertEqual([], self.node.delivery.status('general'))
        # Simulate the race: a route() call lands for the now-removed
        # binding, exactly as route_cache() would if it read `gone` while it
        # still existed and only inserted after binding_remove's forget().
        self.node.delivery.route({'id': uid(), 'channel': 'general', 'human': True,
                                   'delivery_targets': [{'session': gone['id'], 'state': 'pending', 'reason': ''}]})
        self.assertEqual(1, len(self.node.delivery.status('general')))
        for _ in range(3):
            self.node.report()  # must not raise, and must not permanently wedge
        self.assertEqual([], self.node.delivery.status('general'))
        # A real, still-bound session in the same room keeps working normally.
        message = self.node.enqueue('message', {'text': 'still fine', 'targets': [keep['id']]})
        self.node.sync_once()
        self.node.report()
        self.node.sync_once()
        snap = self.node.snapshot()
        self.assertEqual(1, len(snap['receipts']))
        self.assertEqual(message['id'], snap['receipts'][0]['message'])


class RollupTests(NodeTests):
    """Cross-room smart-views rollup: per-room 'rollup' plus top-level
    needsYou/activeCount, computed only from this device's own bindings and
    pending requests (no cross-device participant data exists to roll up)."""

    def room(self, snap, room_id):
        return next(r for r in snap['rooms'] if r['id'] == room_id)

    def test_room_with_blocked_binding_rolls_up_to_blocked(self):
        binding = self.bind()
        self.node.control('binding-state', {'binding': binding['id'], 'state': 'blocked'})
        snap = self.node.snapshot()
        general = self.room(snap, 'general')
        self.assertEqual('blocked', general['rollup']['state'])
        self.assertEqual(1, general['rollup']['needs'])

    def test_room_with_only_idle_bindings_rolls_up_to_idle(self):
        self.bind()
        snap = self.node.snapshot()
        general = self.room(snap, 'general')
        self.assertEqual('unknown', general['rollup']['state'])
        self.assertEqual(0, general['rollup']['needs'])

    def test_empty_default_general_room_rolls_up_cleanly(self):
        snap = self.node.snapshot()
        general = self.room(snap, 'general')
        self.assertEqual('unknown', general['rollup']['state'])
        self.assertEqual(0, general['rollup']['needs'])
        self.assertEqual(0, snap['needsYou'])
        self.assertEqual(0, snap['activeCount'])

    def test_needs_you_counts_pending_requests_and_blocked_bindings_across_rooms(self):
        created = self.node.control('room-create', {'title': 'Second room'})
        self.node.control('room-select', {'room': 'general'})
        blocked = self.bind()
        self.node.control('binding-state', {'binding': blocked['id'], 'state': 'blocked'})
        working = self.node.bind({'native': uid(), 'app': 'codex-queue', 'title': 'Busy synthetic agent', 'room': created['id']})
        self.node.control('binding-state', {'binding': working['id'], 'state': 'working'})
        self.node.request_create(uid(), 'codex-queue', 'Pending synthetic request')
        self.node.sync_once()  # populate the cached room list (snapshot() reads it, not a live hub call)
        snap = self.node.snapshot()
        self.assertEqual(2, snap['needsYou'])  # 1 pending request + 1 blocked binding
        self.assertEqual(1, snap['activeCount'])
        other_room = self.room(snap, created['id'])
        self.assertEqual('working', other_room['rollup']['state'])
        self.assertEqual(0, other_room['rollup']['needs'])
        general = self.room(snap, 'general')
        self.assertEqual('blocked', general['rollup']['state'])
        self.assertEqual(2, general['rollup']['needs'])  # 1 pending request (general) + 1 blocked binding


class DeviceSchemaTests(unittest.TestCase):
    """Regression for H4: the additive requests.model/requests.room migration
    ran without ever bumping user_version past 1, so rolling back to the old
    (pre-migration) helper opened a migrated profile without complaint and
    then every request_create() failed on a column-count mismatch. The
    version must land on 2, and both a fresh device and a reopened,
    already-migrated one must land there too, without error."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def close(self, node):
        node.stop.set()
        node.db.close()
        node.delivery.db.close()
        if node.hub:
            node.hub.db.close()

    def test_fresh_device_lands_on_version_2_and_reopen_is_idempotent(self):
        home = Path(self.tmp.name)/'A'
        node = Node(home, MemoryVault(), allow_loopback=True)
        try:
            self.assertEqual(2, node.db.execute('PRAGMA user_version').fetchone()[0])
            columns = [r[1] for r in node.db.execute('PRAGMA table_info(requests)')]
            self.assertIn('model', columns)
            self.assertIn('room', columns)
        finally:
            self.close(node)
        reopened = Node(home, MemoryVault(), allow_loopback=True)
        try:
            self.assertEqual(2, reopened.db.execute('PRAGMA user_version').fetchone()[0])
        finally:
            self.close(reopened)

    def test_old_pre_migration_profile_upgrades_cleanly_to_version_2(self):
        home = Path(self.tmp.name)/'B'
        home.mkdir(parents=True)
        seed = sqlite3.connect(str(home/'device.sqlite3'))
        seed.executescript('''
        CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE outbox(id TEXT PRIMARY KEY, event TEXT, state TEXT, error TEXT);
        CREATE TABLE cache(seq INTEGER PRIMARY KEY, id TEXT UNIQUE, event TEXT);
        CREATE TABLE bindings(id TEXT PRIMARY KEY, data TEXT, paused INTEGER DEFAULT 0);
        CREATE TABLE offered(binding TEXT PRIMARY KEY, seq INTEGER DEFAULT 0, cursor INTEGER DEFAULT 0);
        CREATE TABLE reports(id TEXT PRIMARY KEY, state TEXT);
        CREATE TABLE requests(native TEXT, app TEXT, title TEXT, directory TEXT,
          requested REAL, state TEXT, PRIMARY KEY(native, app));
        PRAGMA user_version=1;
        ''')
        seed.commit()
        seed.close()
        node = Node(home, MemoryVault(), allow_loopback=True)
        try:
            self.assertEqual(2, node.db.execute('PRAGMA user_version').fetchone()[0])
            columns = [r[1] for r in node.db.execute('PRAGMA table_info(requests)')]
            self.assertIn('model', columns)
            self.assertIn('room', columns)
        finally:
            self.close(node)

    def test_future_device_schema_is_refused(self):
        home = Path(self.tmp.name)/'C'
        home.mkdir(parents=True)
        seed = sqlite3.connect(str(home/'device.sqlite3'))
        seed.execute('PRAGMA user_version=99')
        seed.close()
        with self.assertRaises(ValueError):
            Node(home, MemoryVault(), allow_loopback=True)
