import importlib
import json
import os
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

_TMP = tempfile.TemporaryDirectory()
os.environ['AGENT_ROOM_HOME'] = _TMP.name
import roomd
import room_mcp as bridge
from delivery import Delivery, dispatch_one


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        roomd.ROOT = self.tmp.name
        roomd.CHANNELS = os.path.join(self.tmp.name, 'channels')
        roomd.STATE_PATH = os.path.join(self.tmp.name, 'state.json')
        self.store = roomd.Store()
        self.d = self.store.delivery
        self.addCleanup(self.d.db.close)
        self.target = '10000000-0000-0000-0000-000000000001'
        self.d.register('receiver', 'test', 'same-name', 'codex-queue', self.target)
        self.d.register('sender', 'test', 'sender')

    def post(self, **kwargs):
        return self.store.post('test', 'sender', 'synthetic only', from_session='sender', to_session='receiver', **kwargs)

    def ready(self):
        with self.d.db:
            self.d.db.execute('UPDATE deliveries SET updated=0')

    def lookup(self, channel, mid):
        return next((m for m in self.store.read(channel, limit=500) if m['id'] == mid), None)

    def test_post_idempotency_and_read_not_acknowledged(self):
        a = self.post(request_id='retry')
        b = self.post(request_id='retry')
        self.assertEqual(a, b)
        self.assertEqual(len(self.d.status('test')), 1)
        self.assertEqual(self.store.cursor('receiver', 'test'), 0)
        self.store.read('test')
        self.assertEqual(self.d.status('test')[0]['state'], 'pending')

    def test_names_never_route_and_channel_boundary(self):
        self.d.register('other', 'test', 'same-name')
        m = self.store.post('test', 'sender', 'synthetic', to='same-name', from_session='sender')
        self.assertEqual(self.d.status('test', m['id'])[0]['state'], 'unavailable')
        self.d.register('elsewhere', 'secret', 'elsewhere', 'codex-queue', self.target)
        m = self.store.post('test', 'sender', 'synthetic', to_session='elsewhere', from_session='sender')
        self.assertEqual(self.d.status('test', m['id'])[0]['session'], '')
        self.assertEqual(self.d.status('secret'), [])

    def test_oldest_first_all_250_and_tail_for_browser(self):
        for i in range(250):
            self.store.post('test', 'sender', str(i), from_session='sender')
        self.assertEqual([m['seq'] for m in self.store.read('test')], list(range(1,201)))
        self.assertEqual(len(self.store.read('test', since=200)), 50)
        self.assertEqual(self.store.read('test', limit=2, tail=True)[0]['seq'],249)

    def test_cursor_monotonic_and_distinct_sessions(self):
        self.store._state['offered'] = {'receiver|test': 10}
        self.store.cursor('receiver', 'test', 10)
        self.store.cursor('receiver', 'test', 2)
        self.assertEqual(self.store.cursor('receiver', 'test'), 10)
        self.assertEqual(self.store.cursor('other', 'test'), 0)
        with self.assertRaises(ValueError):
            self.store.cursor('receiver', 'test', 11)

    def test_claim_atomic_and_ack_race(self):
        self.post(); self.ready()
        row = self.d.claim()
        self.assertIsNone(self.d.claim())
        with self.assertRaises(ValueError):
            self.d.ack('sender', 'test', [row['id']])
        with self.assertRaises(ValueError):
            self.d.ack('receiver', 'secret', [row['id']])
        self.d.ack('receiver', 'test', [row['id']])
        self.d.finish(row['id'], 'submitted')
        self.assertEqual(self.d.status('test')[0]['state'], 'acknowledged')
        self.assertEqual(self.d.inbox('receiver','test'), [])

    def test_restart_uncertain_never_replays_and_route_recovery(self):
        msg = self.post(); self.ready(); self.d.claim()
        d2 = Delivery(self.tmp.name)
        self.addCleanup(d2.db.close)
        self.assertEqual(d2.status('test')[0]['state'], 'uncertain')
        d2.route(msg)
        self.assertEqual(len(d2.status('test')), 1)
        self.assertIsNone(d2.claim())
        with d2.db:
            d2.db.execute('DELETE FROM deliveries')
        d2.route(msg)
        self.assertEqual(d2.status('test')[0]['session'], 'receiver')

    def test_binding_immutable_and_task_unique(self):
        with self.assertRaises(ValueError):
            self.d.register('receiver','test','other','codex-queue',self.target)
        with self.assertRaises(ValueError):
            self.d.register('alias','test','same-name','codex-queue',self.target)
        with self.assertRaises(ValueError):
            self.d.register('bad','test','bad','codex-queue','same-name')

    def test_human_first_and_closed_session(self):
        self.post()
        self.store.post('test','human','synthetic human message')
        self.ready()
        row = self.d.claim()
        self.assertTrue(self.lookup('test',row['message'])['human'])
        self.d.close('receiver','test')
        self.assertIsNone(self.d.claim())

    def test_success_is_only_submitted_and_no_duplicate_dispatch(self):
        self.post(); self.ready()
        with patch('delivery.subprocess.run', return_value=subprocess.CompletedProcess([],0)) as run:
            self.assertTrue(dispatch_one(self.d,self.lookup))
            self.assertFalse(dispatch_one(self.d,self.lookup))
            run.assert_called_once()
            args = run.call_args[0][0]
            self.assertIn(self.target,args)
        self.assertEqual(self.d.status('test')[0]['state'],'submitted')

    def test_safe_retry_bounded_and_timeout_not_replayed(self):
        self.post()
        with patch('delivery.subprocess.run', side_effect=FileNotFoundError) as run:
            for i in range(6):
                self.ready(); dispatch_one(self.d,self.lookup)
            self.assertEqual(run.call_count,3)
        self.assertEqual(self.d.status('test')[0]['state'],'unavailable')
        self.post(); self.ready()
        with patch('delivery.subprocess.run',side_effect=subprocess.TimeoutExpired('codex',20)) as run:
            dispatch_one(self.d,self.lookup)
            self.ready(); dispatch_one(self.d,self.lookup)
            run.assert_called_once()
        self.assertEqual(self.d.status('test')[-1]['state'],'uncertain')

    def test_close_between_journal_and_outbox_is_visible(self):
        msg = self.post()
        with self.d.db:
            self.d.db.execute('DELETE FROM deliveries')
        self.d.close('receiver', 'test')
        self.d.route(msg)
        self.assertEqual(self.d.status('test')[0]['state'], 'unavailable')
        self.assertIsNone(self.d.claim())

    def test_disconnected_channel_and_lost_send_visible(self):
        self.d.register('claude', 'test', 'claude', 'claude-channel')
        self.store.post('test', 'sender', 'synthetic', from_session='sender', to_session='claude')
        with self.d.db:
            self.d.db.execute("UPDATE sessions SET seen=0 WHERE id='claude'")
        self.d.expire_channels()
        self.assertEqual(self.d.status('test')[0]['state'], 'unavailable')
        self.assertFalse(any(r['id']=='claude' for r in self.d.sessions('test')))
        self.post(); self.ready(); row=self.d.claim()
        with self.d.db:
            self.d.db.execute('UPDATE deliveries SET updated=0 WHERE id=?', (row['id'],))
        self.d.expire_channels()
        self.assertEqual(next(r for r in self.d.status('test') if r['id']==row['id'])['state'], 'uncertain')

    def test_claude_claim_cannot_cross_channel_or_adapter(self):
        self.post(); self.ready()
        self.assertIsNone(self.d.claim('receiver','test','claude-channel'))
        self.d.register('claude','test','claude','claude-channel')
        msg = self.store.post('test','sender','synthetic',from_session='sender',to_session='claude')
        self.ready()
        self.assertIsNone(self.d.claim('claude','secret','claude-channel'))
        self.assertEqual(self.d.claim('claude','test','claude-channel')['message'],msg['id'])


class BridgeTests(unittest.TestCase):
    def test_health_probe_never_reenters_startup(self):
        with patch('room_mcp.urllib.request.urlopen',side_effect=ConnectionRefusedError), patch('room_mcp.ensure_daemon') as start:
            self.assertFalse(bridge.daemon_alive())
            start.assert_not_called()

    def test_complete_oldest_page_no_silent_truncation(self):
        messages = [dict(seq=i, at='now', **{'from':'synthetic'}, text='x'*20000) for i in range(1,5)]
        page = bridge.page(messages)
        self.assertEqual(page[0]['seq'],1)
        self.assertEqual(len(page),1)
        self.assertIn('x'*20000,bridge.render(page))
        messages[0]['text']='x'*200000
        self.assertEqual(len(bridge.page(messages)),1)
        self.assertIn('x'*200000,bridge.render(bridge.page(messages)))

    def test_post_and_join_never_update_cursor(self):
        saved = set(bridge.JOINED)
        bridge.JOINED.add('test')
        self.addCleanup(lambda: (bridge.JOINED.clear(), bridge.JOINED.update(saved)))
        with patch('room_mcp.call',return_value={'posted':{'seq':5},'delivery':[]}), patch('room_mcp.cursor_set') as set_cursor:
            bridge.run_tool('room_post',{'channel':'test','text':'synthetic'})
            set_cursor.assert_not_called()

    def test_ack_other_session_rejected(self):
        with self.assertRaises(ValueError):
            bridge.run_tool('room_ack',{'session':'another-session'})

if __name__ == '__main__':
    unittest.main()
