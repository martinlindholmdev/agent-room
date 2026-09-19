"""B1 regressions from phase5-probe.py. Isolated homes; never installed data."""
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop.node import Node
from desktop.secrets import MemoryVault


class DurableDisconnectTests(unittest.TestCase):
    def setUp(self):
        Path('work').mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix='b1-', dir='work')
        self.home = Path(self.tmp.name)
        self.vault = MemoryVault()
        self.node = Node(self.home, self.vault)
        self.node.setup('Isolated B1')
        self.data = {'native': 'b1-synthetic', 'app': 'mcp', 'title': 'B1 fixture'}
        self.binding = self.node.bind(self.data)
        self.identity = self.binding['id']
        self.node.enqueue('message', {'text': 'Keep authored history', 'targets': []}, self.identity)
        self.node.enqueue('message', {'text': 'Keep targeted history', 'targets': [self.identity]})
        self.node.sync_once()
        self.history = self.node.rows('SELECT * FROM cache ORDER BY seq')
        self.hub_history = self.node.hub.rows('SELECT * FROM events ORDER BY seq')

    def close(self):
        self.node.db.close()
        self.node.delivery.db.close()
        self.node.hub.db.close()

    def tearDown(self):
        self.close()
        self.tmp.cleanup()

    def restart(self):
        self.close()
        self.node = Node(self.home, self.vault)

    def active(self):
        return self.node.hub.rows('SELECT active FROM sessions WHERE id=?', (self.identity,))[0]['active']

    def assert_history(self):
        self.assertEqual(self.history, self.node.rows('SELECT * FROM cache ORDER BY seq'))
        self.assertEqual(self.hub_history, self.node.hub.rows('SELECT * FROM events ORDER BY seq'))

    def remove_offline(self):
        with patch.object(self.node, 'call', side_effect=ConnectionError('synthetic offline')):
            result = self.node.binding_remove(self.identity)
        self.assertEqual({'removed': True, 'id': self.identity, 'pending': True}, result)
        self.assertEqual([], self.node.bindings())
        self.assertEqual([], self.node.delivery.status('general'))
        pending = self.node.snapshot()['pending_removals']
        self.assertEqual([{'id': self.identity, 'title': 'B1 fixture', 'app': 'mcp', 'room': 'general'}], pending)
        self.assert_history()

    def test_online_removal_is_immediate_and_reconnection_keeps_history(self):
        self.assertEqual({'removed': True, 'id': self.identity}, self.node.binding_remove(self.identity))
        self.assertEqual(0, self.active())
        self.assertEqual([], self.node.snapshot()['pending_removals'])
        with self.assertRaises(ValueError):
            self.node.set_binding_state(self.identity, 'working')
        self.assertEqual(self.identity, self.node.bind(self.data)['id'])
        self.node.sync_once()
        self.assertEqual(1, self.active())
        self.assert_history()

    def test_existing_device_adds_pending_table_without_losing_history(self):
        with self.node.db:
            self.node.db.execute('DROP TABLE pending_removals')
        self.restart()
        self.assertEqual([], self.node.pending_removals())
        self.remove_offline()
        self.restart()
        self.node.sync_once()
        self.assertEqual(0, self.active())
        self.assert_history()

    def test_offline_removal_retries_after_recovery_and_preserves_history(self):
        self.remove_offline()
        self.assertEqual(1, self.active())
        with patch.object(self.node, 'call', side_effect=ConnectionError):
            with self.assertRaises(ConnectionError):
                self.node.sync_once()
        self.assertEqual(1, len(self.node.pending_removals()))
        self.node.sync_once()
        self.node.sync_once()
        self.assertEqual(0, self.active())
        self.assertEqual([], self.node.snapshot()['pending_removals'])
        receipt = self.node.hub.rows('SELECT state FROM receipts WHERE target=?', (self.identity,))[0]
        self.assertEqual('unavailable', receipt['state'])
        self.assert_history()

    def test_restart_keeps_pending_intent_without_registering_removed_session(self):
        self.remove_offline()
        self.restart()
        self.assertEqual([], self.node.bindings())
        self.assertEqual(1, len(self.node.snapshot()['pending_removals']))
        with patch.object(self.node, 'call', wraps=self.node.call) as calls:
            self.node.sync_once()
        self.assertNotIn('bind', [c.args[0] for c in calls.call_args_list])
        self.assertEqual(0, self.active())
        self.restart()
        self.node.sync_once()
        self.assertEqual([], self.node.pending_removals())
        self.assertEqual(0, self.active())
        self.assert_history()

    def test_repeated_removal_by_id_and_native_is_safe_offline_and_online(self):
        self.remove_offline()
        with patch.object(self.node, 'call', side_effect=ConnectionError):
            for data in ({'binding': self.identity}, self.data):
                self.assertTrue(self.node.control('binding-remove', data)['pending'])
        self.assertEqual(1, len(self.node.pending_removals()))
        self.assertEqual({'removed': True, 'id': self.identity}, self.node.binding_remove(self.identity))
        self.assertEqual({'removed': False}, self.node.binding_remove(self.identity))
        self.assertEqual({'removed': False}, self.node.binding_remove('unknown'))
        self.node.sync_once()
        self.assertEqual(0, self.active())
        self.assert_history()

    def test_reconnection_settles_old_removal_before_reactivating_identity(self):
        self.remove_offline()
        self.restart()
        with patch.object(self.node, 'call', side_effect=ConnectionError):
            with self.assertRaises(ConnectionError):
                self.node.bind(self.data)
        self.assertEqual([], self.node.bindings())
        with patch.object(self.node, 'call', wraps=self.node.call) as calls:
            reconnected = self.node.bind(self.data)
        self.assertEqual(['session-remove', 'bind'], [c.args[0] for c in calls.call_args_list])
        self.assertEqual(self.identity, reconnected['id'])
        self.assertEqual([], self.node.pending_removals())
        self.node.sync_once()
        self.restart()
        self.node.sync_once()
        self.assertEqual(1, self.active())
        self.assert_history()

    def test_lost_removal_response_replays_safely_after_restart(self):
        call = self.node.call

        def lost_response(action, data=None):
            result = call(action, data)
            if action == 'session-remove':
                raise ConnectionError('synthetic lost response after commit')
            return result

        with patch.object(self.node, 'call', side_effect=lost_response):
            self.assertTrue(self.node.binding_remove(self.identity)['pending'])
        self.assertEqual(0, self.active())
        self.restart()
        self.node.sync_once()
        self.assertEqual([], self.node.pending_removals())
        self.assertEqual(0, self.active())
        self.assert_history()

    def test_pending_removal_uses_original_room_after_room_switch(self):
        self.remove_offline()
        other = self.node.room_create('Other B1 room')
        self.restart()
        with patch.object(self.node, 'call', wraps=self.node.call) as calls:
            self.node.sync_once()
        removal = next(c for c in calls.call_args_list if c.args[0] == 'session-remove')
        self.assertEqual('general', removal.args[1]['room'])
        self.assertEqual(other['id'], self.node.snapshot()['room'])
        self.assertEqual(0, self.active())
        self.assertEqual(0, next(s['active'] for s in self.node.get('snapshots')['general']['sessions'] if s['id'] == self.identity))
        self.assert_history()

    def test_unsent_removed_sender_is_preserved_as_failed_not_stuck_sending(self):
        draft = self.node.enqueue('message', {'text': 'Keep unsent text', 'targets': []}, self.identity)
        self.remove_offline()
        self.node.sync_once()
        row = self.node.rows('SELECT * FROM outbox WHERE id=?', (draft['id'],))[0]
        self.assertEqual('failed', row['state'])
        self.assertIn('Keep unsent text', row['event'])
        self.assertEqual(0, self.active())
        self.assert_history()

    def test_crash_after_intent_commit_recovers_delivery_cleanup(self):
        with patch.object(self.node.delivery, 'forget', side_effect=RuntimeError('synthetic crash')):
            with self.assertRaises(RuntimeError):
                self.node.binding_remove(self.identity)
        self.assertEqual([], self.node.bindings())
        self.assertEqual(1, len(self.node.pending_removals()))
        self.restart()
        self.assertEqual([], self.node.delivery.status('general'))
        self.node.sync_once()
        self.assertEqual(0, self.active())
        self.assert_history()

    def test_inflight_sync_registration_cannot_resurrect_removed_session(self):
        entered, release, remove_started, removed = (threading.Event() for _ in range(4))
        errors = []
        call = self.node.call

        def held_call(action, data=None):
            if action == 'bind':
                entered.set()
                if not release.wait(5):
                    raise TimeoutError('test release timed out')
            return call(action, data)

        def sync():
            try:
                self.node.sync_once()
            except Exception as exc:
                errors.append(exc)

        def remove():
            remove_started.set()
            try:
                self.node.binding_remove(self.identity)
                removed.set()
            except Exception as exc:
                errors.append(exc)

        with patch.object(self.node, 'call', side_effect=held_call):
            sync_thread = threading.Thread(target=sync)
            remove_thread = threading.Thread(target=remove)
            sync_thread.start()
            try:
                self.assertTrue(entered.wait(5))
                remove_thread.start()
                self.assertTrue(remove_started.wait(5))
                self.assertFalse(removed.wait(.05))
            finally:
                release.set()
                sync_thread.join(5)
                if remove_thread.ident:
                    remove_thread.join(5)
        self.assertFalse(sync_thread.is_alive())
        self.assertFalse(remove_thread.is_alive())
        self.assertEqual([], errors)
        self.assertTrue(removed.is_set())
        self.node.sync_once()
        self.assertEqual(0, self.active())
        self.assertEqual([], self.node.bindings())
        self.assert_history()
