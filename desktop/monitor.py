"""Private, per-MCP-connection trigger feed for Claude app's native Monitor.

Only a wake hint crosses this socket. Room data and receipts still require the
exact-bound ordinary MCP tools. A Monitor command runs under host permissions.
"""
import os
import hashlib
import re
import secrets
import select
import shlex
import socket
import stat
import sys
import threading
import time
from pathlib import Path

HINT = (b'Agent Room message available. In this same MCP conversation, drain complete room_read pages, '
        b'advance read_through only for pages read, and acknowledge only delivery IDs whose messages you read.\n')
END = b'Agent Room watch window ended. Renew with room_monitor_setup and native Monitor in this same conversation.\n'
SOCKET_NAME = re.compile(r's-[0-9a-f]{24}\.sock\Z')
WATCH_SECONDS = 30 * 60


def monitor_directory(root):
    # macOS sun_path is only 104 bytes. A profile in Application Support can
    # exceed it; use a short, profile-specific private directory instead.
    profile = hashlib.sha256(os.fsencode(Path(root).resolve())).hexdigest()[:12]
    directory = Path('/tmp').resolve() / ('ar-monitor-u%d-%s' % (os.getuid(), profile))
    if directory.is_symlink():
        raise ValueError('monitor directory cannot be a symlink')
    directory.mkdir(mode=0o700, exist_ok=True)
    info = directory.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('monitor directory must be private to this user')
    return directory


def checked_socket_path(root, value):
    directory = monitor_directory(root).resolve()
    path = Path(value)
    if not path.is_absolute() or path.parent != directory or not SOCKET_NAME.fullmatch(path.name):
        raise ValueError('invalid Agent Room monitor socket path')
    info = path.lstat()
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('monitor socket must be private to this user')
    return path


def watch_socket(root, value, seconds=WATCH_SECONDS):
    """Foreground stdout client used only by a native Claude app Monitor call."""
    if type(seconds) is not int or not 60 <= seconds <= WATCH_SECONDS:
        raise ValueError('monitor deadline must be 60 to 1800 seconds')
    path = checked_socket_path(root, value)
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(5)
        client.connect(str(path))
        client.settimeout(10)
        # The native host's Monitor deadline starts when its command runs.
        # Leave a grace window so its own expiry notice can arrive first.
        deadline = time.monotonic() + seconds + 20
        buffer = b''
        while time.monotonic() < deadline:
            try:
                part = client.recv(256)
            except socket.timeout:
                continue
            if not part:
                break
            buffer += part
            if len(buffer) > 512:
                raise ValueError('monitor trigger too long')
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                if line + b'\n' not in (HINT, END):
                    raise ValueError('invalid monitor trigger')
                sys.stdout.write((line + b'\n').decode())
                sys.stdout.flush()


class MonitorFeed:
    def __init__(self, root, binding, native, generation, fetch, executable=None):
        self.root = Path(root).resolve()
        self.binding, self.native, self.generation = binding, native, generation
        self.fetch = fetch
        self.command_prefix = ([executable] if executable else [sys.executable])
        if not executable and not getattr(sys, 'frozen', False):
            self.command_prefix.append(str(Path(__file__).resolve().parent.parent / 'desktop_main.py'))
        self.stopped = threading.Event()
        self.connected = threading.Event()
        self.listener = None
        self.client = None
        self.thread = None
        self.path = None
        self.owns_path = False
        self.notified = (0, 0)

    def start(self, seconds=WATCH_SECONDS):
        if type(seconds) is not int or not 60 <= seconds <= WATCH_SECONDS:
            raise ValueError('monitor deadline must be 60 to 1800 seconds')
        # Verify the exact bound generation before advertising a command.
        self.fetch()
        directory = monitor_directory(self.root)
        self.path = directory / ('s-' + secrets.token_hex(12) + '.sock')
        if len(os.fsencode(self.path)) > 103:
            raise ValueError('profile path too long for private monitor socket')
        listener = socket.socket(socket.AF_UNIX)
        bound = False
        try:
            listener.bind(str(self.path))
            bound = True
            self.owns_path = True
            os.chmod(self.path, 0o600)
            listener.listen(1)
        except Exception:
            listener.close()
            if bound and self.path.exists() and self.path.is_socket():
                self.path.unlink()
            self.owns_path = False
            raise
        self.listener = listener
        self.seconds = seconds
        self.deadline = time.monotonic() + 300  # Bound an unused setup command.
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()
        command = ' '.join(shlex.quote(part) for part in
                           (*self.command_prefix, '--home', str(self.root), '--watch-socket', str(self.path),
                            '--watch-seconds', str(seconds)))
        return {'command': command,
                'timeout_ms': seconds * 1000,
                'instructions': 'Start this command with the native Claude app Monitor tool in this same conversation, with timeout_ms from this result and under normal host permissions. Monitor ends at its deadline (at most 30 minutes). When Claude receives the expiry notice, call room_monitor_setup again and start a new native Monitor. This feed emits one catch-up hint for pending unread messages on each new watch; drain complete room_read pages and acknowledge only deliveries whose content you read. An active feed is not proof of host wake or receipt.'}

    def status(self):
        return {'connected': self.connected.is_set() and not self.stopped.is_set() and
                time.monotonic() < self.deadline,
                'seconds_remaining': max(0, int(self.deadline - time.monotonic())) if not self.stopped.is_set() else 0,
                'note': 'Socket connection is transport evidence only; actual native idle wake and receiver receipt require separate verification.'}

    def _serve(self):
        listener = self.listener
        client = None
        expired = False
        try:
            while not self.stopped.is_set() and time.monotonic() < self.deadline:
                if client is None:
                    ready, _, _ = select.select([listener], [], [], 1)
                    if not ready:
                        continue
                    client, _ = listener.accept()
                    self.client = client
                    client.setblocking(False)
                    self.connected.set()
                    self.deadline = time.monotonic() + self.seconds + 15
                    self.notified = (0, 0)  # Catch up once on native Monitor reconnect.
                ready, _, _ = select.select([listener, client], [], [], 1)
                if listener in ready:
                    extra, _ = listener.accept()
                    extra.close()  # Exactly one native Monitor consumer at a time.
                if client in ready:
                    try:
                        if client.recv(1) != b'':
                            raise ValueError('monitor client must be read-only')
                        else:
                            client.close()
                            client = None
                            self.client = None
                            self.connected.clear()
                            continue
                    except BlockingIOError:
                        pass
                result = self.fetch()  # Local control validates native and generation on every poll.
                pending = (result['oldest'], result['latest'])
                if pending[1] and pending != self.notified and client is not None:
                    client.sendall(HINT)
                    self.notified = pending
                elif not pending[1]:
                    self.notified = (0, 0)
            expired = not self.stopped.is_set() and time.monotonic() >= self.deadline
            if expired and client is not None:
                client.sendall(END)
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            pass  # Stale binding, helper shutdown or revoked generation closes feed.
        finally:
            self.connected.clear()
            if client is not None:
                try:
                    client.close()
                except OSError:
                    pass
            self.close()

    def close(self):
        self.stopped.set()
        for endpoint in (self.client, self.listener):
            if endpoint is not None:
                try:
                    endpoint.close()
                except OSError:
                    pass
        if self.path is not None and self.owns_path:
            try:
                if self.path.is_socket():
                    self.path.unlink()
                self.owns_path = False
            except OSError:
                pass
