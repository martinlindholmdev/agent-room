"""B5: simulated time, isolated homes under work; no live data or real agents."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop.node import Node
from desktop.secrets import MemoryVault


class HonestPresenceTests(unittest.TestCase):
    def setUp(self):
        Path('work').mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix='b5-', dir='work')
        self.home = Path(self.tmp.name)
        self.vault = MemoryVault()
        self.node = Node(self.home, self.vault)
        self.node.setup('Synthetic B5')

    def close(self):
        self.node.db.close()
        self.node.delivery.db.close()
        self.node.hub.db.close()

    def tearDown(self):
        self.close()
        self.tmp.cleanup()

    def bind(self, app='mcp'):
        return self.node.bind({'native': 'b5-' + app, 'app': app, 'title': 'Synthetic B5'})

    def test_registration_polling_and_sync_are_not_contact(self):
        b = self.bind()
        for _ in range(2):
            self.node.sync_once()
            result = self.node.snapshot()['bindings'][0]
            self.assertEqual('unknown', result['state'])
            self.assertNotIn('state_reported_at', result)
            self.assertNotIn('last_contact_at', result)
        self.assertEqual('unknown', self.node.snapshot()['rooms'][0]['rollup']['state'])

    def test_read_refreshes_contact_not_report_and_rebind_preserves_both(self):
        b = self.bind()
        with patch('desktop.node.time.time', return_value=1000):
            self.node.set_binding_state(b['id'], 'working')
        with patch('desktop.node.time.time', return_value=1300):
            self.node.tool(b['id'], 'room_read', {})
            self.bind()
        result = self.node.binding(b['id'])
        self.assertEqual('working', result['state'])
        self.assertEqual(1000, result['state_reported_at'])
        self.assertEqual(1300, result['last_contact_at'])

    def test_day_idle_and_restart_never_delete_or_rejuvenate(self):
        for app in ('mcp', 'pull', 'claude-channel'):
            b = self.bind(app)
            with patch('desktop.node.time.time', return_value=1000):
                self.node.set_binding_state(b['id'], 'working')
        with patch('desktop.node.time.time', return_value=87400):
            self.node.delivery.expire_channels()
            self.node.sync_once()
            self.close()
            self.node = Node(self.home, self.vault)
            self.node.sync_once()
            result = self.node.snapshot()['bindings']
        self.assertEqual(3, len(result))
        for b in result:
            self.assertEqual(('working', 1000, 1000), (b['state'], b['state_reported_at'], b['last_contact_at']))
            self.assertFalse(b['bridge_connected'])
        self.assertTrue(all(r['active'] for r in self.node.hub.rows('SELECT active FROM sessions')))

    def test_legacy_report_is_not_given_an_invented_timestamp(self):
        b = self.bind()
        b['state'] = 'blocked'
        self.node.save_binding(b)
        self.close()
        self.node = Node(self.home, self.vault)
        result = self.node.binding(b['id'])
        self.assertEqual('blocked', result['state'])
        self.assertNotIn('state_reported_at', result)
        self.assertNotIn('last_contact_at', result)

    def test_validated_wait_and_watch_are_contact_not_work_reports(self):
        b = self.bind()
        with patch('desktop.node.time.time', return_value=1000):
            self.node.wait_next(b['id'], b['native'], b['generation'], 0)
        self.assertEqual(1000, self.node.binding(b['id'])['last_contact_at'])
        with patch('desktop.node.time.time', return_value=1200):
            self.node.control('watch-next', {'binding': b['id'], 'native': b['native'], 'generation': b['generation']})
        with self.assertRaises(ValueError):
            self.node.wait_next(b['id'], 'wrong', b['generation'], 0)
        self.assertEqual(1200, self.node.binding(b['id'])['last_contact_at'])
        self.assertNotIn('state_reported_at', self.node.binding(b['id']))

    def test_bridge_open_poll_heartbeat_record_contact_and_reject_bad_lease(self):
        b = self.bind('claude-channel')
        with patch('desktop.node.time.time', return_value=1000):
            lease = self.node.bridge_open(b['id'], b['native'], b['app'])['lease']
        self.assertEqual(1000, self.node.binding(b['id'])['last_contact_at'])
        with patch('desktop.node.time.time', return_value=1100):
            self.node.bridge_next(b['id'], lease, 0)
        self.assertEqual(1100, self.node.binding(b['id'])['last_contact_at'])
        with patch('desktop.node.time.time', return_value=1200):
            self.node.control('bridge-heartbeat', {'binding': b['id'], 'lease': lease})
        with self.assertRaises(ValueError):
            self.node.control('bridge-heartbeat', {'binding': b['id'], 'lease': 'invalid'})
        self.assertEqual(1200, self.node.binding(b['id'])['last_contact_at'])
        self.assertNotIn('state_reported_at', self.node.binding(b['id']))
