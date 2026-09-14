import os
import unittest
from unittest.mock import patch
from desktop.mcp import resolve_binding


class HostIdentityTests(unittest.TestCase):
    bindings=[{'id':'a','native':'task-a','app':'codex-queue'},
              {'id':'b','native':'task-b','app':'codex-queue'},
              {'id':'c','native':'claude-c','app':'claude-channel'}]

    def test_global_configuration_selects_only_current_host_session(self):
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'task-b'},clear=True):
            self.assertEqual(resolve_binding(self.bindings)['id'],'b')
            with self.assertRaises(SystemExit):resolve_binding(self.bindings,'a')
        with patch.dict(os.environ,{'CLAUDE_CODE_SESSION_ID':'claude-c'},clear=True):
            self.assertEqual(resolve_binding(self.bindings,claude_channel=True)['id'],'c')
            with self.assertRaises(SystemExit):resolve_binding(self.bindings)

    def test_missing_unregistered_and_ambiguous_identity_fail_closed(self):
        for env in ({},{'CODEX_THREAD_ID':'unregistered'}):
            with patch.dict(os.environ,env,clear=True):
                with self.assertRaises(SystemExit):resolve_binding(self.bindings)
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'task-a'},clear=True):
            with self.assertRaises(SystemExit):resolve_binding(self.bindings+[self.bindings[0]])
