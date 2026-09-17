"""Synthetic native-Monitor stdout feed; no Claude process or prompt."""
import io
import os
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop.monitor import HINT, END, MonitorFeed, checked_socket_path, monitor_directory, watch_socket


class MonitorFeedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.latest = 0
        self.oldest = 0
        self.valid = True
        self.calls = 0
        def fetch():
            self.calls += 1
            if not self.valid:
                raise ValueError('connector generation changed')
            return {'oldest': self.oldest, 'latest': self.latest}
        self.feed = MonitorFeed(self.root, 'exact-binding', 'exact-native', 4, fetch,
                                executable='/Applications/Agent Room.app/Contents/Resources/helper/agent-room-helper')

    def tearDown(self):
        self.feed.close()
        if self.feed.thread:
            self.feed.thread.join(timeout=3)
        self.tmp.cleanup()

    def connected(self):
        client = socket.socket(socket.AF_UNIX)
        client.settimeout(3)
        client.connect(str(self.feed.path))
        return client

    def test_private_one_consumer_trigger_dedupe_and_shutdown(self):
        setup = self.feed.start(60)
        self.assertEqual(60000, setup['timeout_ms'])
        self.assertIn('--watch-socket', setup['command'])
        self.assertNotIn('exact-native', setup['command'])
        self.assertNotIn('exact-binding', setup['command'])
        self.assertEqual(0o600, self.feed.path.stat().st_mode & 0o777)
        self.assertEqual(0o700, self.feed.path.parent.stat().st_mode & 0o777)
        self.assertEqual(self.feed.path, checked_socket_path(self.root, str(self.feed.path)))
        with self.assertRaises(ValueError):checked_socket_path(self.root, '/tmp/other.sock')
        with self.connected() as first:
            self.latest = 1
            self.oldest = 1
            self.assertEqual(HINT, first.recv(256))
            self.assertNotIn(b'exact-native', HINT)
            self.assertNotIn(b'876c0446aa20468490a382cf6f9f89c2', HINT)
            first.settimeout(1.5)
            with self.assertRaises(socket.timeout):first.recv(256)
            with self.connected() as duplicate:
                self.assertEqual(b'', duplicate.recv(256))
            self.latest = 2
            self.oldest = 1
            first.settimeout(3)
            self.assertEqual(HINT, first.recv(256))
        self.feed.close()
        self.feed.thread.join(timeout=3)
        self.assertFalse(self.feed.path.exists())

    def test_stale_generation_closes_watch_and_removes_socket(self):
        self.feed.start(60)
        with self.connected() as client:
            self.valid = False
            self.assertEqual(b'', client.recv(256))
        self.feed.thread.join(timeout=3)
        self.assertFalse(self.feed.path.exists())

    def test_existing_unread_renewal_gap_and_partial_ack_retrigger(self):
        self.oldest, self.latest = 1, 2  # Already pending before setup.
        self.feed.start(60)
        with self.connected() as first:
            self.assertEqual(HINT, first.recv(256))
            self.oldest = 2  # First targeted delivery acknowledged; second remains.
            self.assertEqual(HINT, first.recv(256))
        self.feed.close()
        self.feed.thread.join(timeout=3)
        self.latest = 3  # New target arrives in expiry/renewal gap.
        renewed = MonitorFeed(self.root, 'exact-binding', 'exact-native', 4,
                              self.feed.fetch, executable='agent-room-helper')
        try:
            renewed.start(60)
            with socket.socket(socket.AF_UNIX) as next_client:
                next_client.settimeout(3)
                next_client.connect(str(renewed.path))
                self.assertEqual(HINT, next_client.recv(256))
        finally:
            renewed.close()
            renewed.thread.join(timeout=3)

    def test_active_deadline_starts_at_connect_and_emits_end_hint(self):
        self.feed.start(60)
        self.feed.deadline = time.monotonic() + 2  # Simulate late native permission approval.
        with self.connected() as client:
            deadline = time.monotonic() + 3
            while not self.feed.connected.is_set() and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(self.feed.connected.is_set())
            self.assertGreater(self.feed.status()['seconds_remaining'], 65)
            self.feed.deadline = time.monotonic() - 1  # Synthetic expiry, without waiting 60s.
            self.assertEqual(END, client.recv(256))
        self.feed.thread.join(timeout=3)
        self.assertFalse(self.feed.path.exists())

    def test_deadline_and_bad_duration_fail_closed(self):
        with self.assertRaises(ValueError):self.feed.start(30)
        with self.assertRaises(ValueError):self.feed.start(1801)
        self.feed.start(60)
        self.feed.deadline = time.monotonic() - 1
        self.feed.thread.join(timeout=3)
        self.assertFalse(self.feed.path.exists())

    def test_socket_name_collision_does_not_unlink_other_feed(self):
        occupied = monitor_directory(self.root) / ('s-' + 'a' * 24 + '.sock')
        with socket.socket(socket.AF_UNIX) as owner:
            owner.bind(str(occupied))
            os.chmod(occupied, 0o600)
            with patch('desktop.monitor.secrets.token_hex', return_value='a' * 24):
                with self.assertRaises(OSError):self.feed.start(60)
            self.feed.close()
            self.assertTrue(occupied.is_socket())
        occupied.unlink()

    def test_stdout_client_only_prints_valid_hint_and_exits_on_close(self):
        self.feed.start(60)
        output = io.StringIO()
        errors = []
        def client():
            try:
                with patch('desktop.monitor.sys.stdout', output):
                    watch_socket(self.root, str(self.feed.path), 60)
            except Exception as error:
                errors.append(error)
        thread = threading.Thread(target=client)
        thread.start()
        deadline = time.monotonic() + 3
        while not self.feed.connected.is_set() and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertTrue(self.feed.connected.is_set())
        self.latest = 1
        self.oldest = 1
        deadline = time.monotonic() + 3
        while not output.getvalue() and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertEqual(HINT.decode(), output.getvalue())
        self.feed.close()
        thread.join(timeout=3)
        self.assertFalse(thread.is_alive())
        self.assertEqual([], errors)
