"""Parity between the Tauri IPC allowlist and the actions the renderer can invoke.

The installed app only exposes `invoke("control")`, gated by main.rs's ALLOWED
list. If a frontend action is ever added without also allow-listing it in
Rust, the packaged app silently rejects it with "Unsupported action" (the
dev-server fetch("/control") path bypasses this allowlist entirely, so
exercising the app at localhost:1420 alone can never catch the gap).

This parses both sources as plain text -- no Rust toolchain or Node/tsc
required -- and fails if the frontend can invoke any action Rust would
reject.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_RS = ROOT / 'apps' / 'desktop' / 'src-tauri' / 'src' / 'main.rs'
MAIN_TSX = ROOT / 'apps' / 'desktop' / 'src' / 'main.tsx'


def rust_allowed():
    text = MAIN_RS.read_text()
    match = re.search(r'const ALLOWED:\s*&\[&str\]\s*=\s*&\[(.*?)\];', text, re.DOTALL)
    assert match, 'ALLOWED allowlist not found in main.rs; parser needs updating'
    return set(re.findall(r'"([a-zA-Z0-9_-]+)"', match.group(1)))


def frontend_actions():
    text = MAIN_TSX.read_text()
    # First string-literal argument of every act("...") / api("...") call.
    # Calls that pass a variable (e.g. api(action, data), used internally by
    # act() itself) are intentionally not literals and are skipped -- they
    # forward whatever act() was called with, which is already covered.
    return set(re.findall(r'\b(?:act|api)\(\s*"([a-zA-Z0-9_-]+)"', text))


class AllowlistParityTests(unittest.TestCase):
    def test_every_frontend_control_action_is_allow_listed_in_rust(self):
        allowed = rust_allowed()
        used = frontend_actions()
        self.assertTrue(used, 'no action strings parsed from main.tsx; parser likely broken')
        missing = used - allowed
        self.assertEqual(
            set(), missing,
            'main.tsx invokes control action(s) %s not present in main.rs ALLOWED; '
            'the installed (Tauri) app will reject them with "Unsupported action" '
            'even though a dev-server run against fetch("/control") would work fine'
            % sorted(missing))


if __name__ == '__main__':
    unittest.main()
