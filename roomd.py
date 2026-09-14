#!/usr/bin/env python3
"""Agent Room daemon.

A tiny message bus so AI agents from different vendors can talk to each other,
plus a web page a human can watch and join from.

Zero dependencies: standard library only, runs on the Python that ships with
macOS. Messages are stored as plain JSON lines on disk so they stay readable
without this program.
"""

import json
import fcntl
import os
import re
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from delivery import Delivery, dispatch_one

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("AGENT_ROOM_HOME", os.path.expanduser("~/.agent-room"))
CHANNELS = os.path.join(ROOT, "channels")
STATE_PATH = os.path.join(ROOT, "state.json")
DEFAULT_PORT = int(os.environ.get("AGENT_ROOM_PORT", "8787"))

NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._@-]{0,63}$")
PRESENCE_TTL = 15 * 60          # an agent is "here" for 15 min after activity
# Agents discuss here. Room to think, not a telegram.
MAX_TEXT = 200_000
KINDS = ("say", "ask", "answer", "note", "decision", "status")


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def valid_name(name):
    return bool(name) and bool(NAME_RE.match(name))


class Store(object):
    """Append-only message log, one JSON-lines file per channel.

    A single daemon owns all writes, so a plain lock is enough; readers never
    need to coordinate.
    """

    def __init__(self):
        os.makedirs(CHANNELS, exist_ok=True)
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._cache = {}        # channel -> list of messages
        self._state = self._load_state()
        self.delivery = Delivery(ROOT)
        # Recover only posts that carry a pinned route snapshot, never reroute old history.
        with self._lock:
            for filename in os.listdir(CHANNELS):
                if filename.endswith('.jsonl') and valid_name(filename[:-6]):
                    for msg in self._load_channel_locked(filename[:-6]):
                        self.delivery.route(msg)

    # ---- state (agents, cursors) ----------------------------------------

    def _load_state(self):
        try:
            with open(STATE_PATH, "r") as fh:
                return json.load(fh)
        except Exception:
            return {"agents": {}, "cursors": {}}

    def _save_state_locked(self):
        tmp = STATE_PATH + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(self._state, fh, indent=2, sort_keys=True)
        os.replace(tmp, STATE_PATH)

    # ---- channels --------------------------------------------------------

    def _path(self, channel):
        return os.path.join(CHANNELS, channel + ".jsonl")

    def _load_channel_locked(self, channel):
        if channel in self._cache:
            return self._cache[channel]
        msgs = []
        path = self._path(channel)
        if os.path.exists(path):
            with open(path, "r") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msgs.append(json.loads(line))
                    except ValueError:
                        continue
        self._cache[channel] = msgs
        return msgs

    def channels(self):
        with self._lock:
            names = []
            for fn in sorted(os.listdir(CHANNELS)):
                if not fn.endswith(".jsonl"):
                    continue
                channel = fn[:-6]
                msgs = self._load_channel_locked(channel)
                names.append({
                    "channel": channel,
                    "messages": len(msgs),
                    "last_at": msgs[-1]["at"] if msgs else None,
                    "last_from": msgs[-1]["from"] if msgs else None,
                })
            return names

    def post(self, channel, sender, text, to=None, kind="say", from_session=None, to_session=None, request_id=None):
        if not valid_name(channel):
            raise ValueError("channel name must be letters, numbers, dot, dash or underscore")
        if not valid_name(sender):
            raise ValueError("agent name must be letters, numbers, dot, dash or underscore")
        if to and not valid_name(to):
            raise ValueError('invalid recipient')
        if request_id and (not isinstance(request_id, str) or len(request_id) > 128):
            raise ValueError('invalid request id')
        if from_session:
            if not any(r['id'] == from_session and r['agent'] == sender for r in self.delivery.sessions(channel)):
                raise ValueError('sender session must join this channel first')
        text = (text or "").strip()
        if not text:
            raise ValueError("message text is empty")
        if len(text) > MAX_TEXT:
            raise ValueError("message too long")
        if kind not in KINDS:
            kind = "say"
        with self._cond:
            msgs = self._load_channel_locked(channel)
            if request_id:
                for old in msgs:
                    if old.get('request_id') == request_id and old.get('from_session') == from_session and old['from'] == sender:
                        return old
            msg = {
                "seq": len(msgs) + 1,
                "id": uuid.uuid4().hex[:12],
                "at": now_iso(),
                "channel": channel,
                "from": sender,
                "to": to if (to and valid_name(to)) else None,
                "kind": kind,
                "text": text,
                "from_session": from_session,
                "to_session": to_session,
                "request_id": request_id,
                "human": not from_session and not self._state['agents'].get(sender, {}).get('is_agent', False),
            }
            msg["delivery_targets"] = self.delivery.targets(msg)
            with open(self._path(channel), "a") as fh:
                fh.write(json.dumps(msg, ensure_ascii=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            msgs.append(msg)
            self._touch_locked(sender, channel)
            self.delivery.route(msg)
            self._cond.notify_all()
            return msg

    def read(self, channel, since=0, limit=200, tail=False):
        with self._lock:
            msgs = self._load_channel_locked(channel)
            out = [m for m in msgs if m["seq"] > since]
            return out[-limit:] if tail else out[:limit]

    def wait(self, channel, since=0, timeout=25.0):
        """Block until a message newer than `since` arrives, or time out.

        This is what makes the room feel live: an agent can hand over and then
        wait for the reply inside the same turn, instead of polling.
        """
        deadline = time.time() + max(0.0, min(float(timeout), 300.0))
        with self._cond:
            while True:
                msgs = self._load_channel_locked(channel)
                fresh = [m for m in msgs if m["seq"] > since]
                if fresh:
                    return fresh[:200]
                remaining = deadline - time.time()
                if remaining <= 0:
                    return []
                self._cond.wait(min(remaining, 1.0))

    # ---- presence --------------------------------------------------------

    def _touch_locked(self, agent, channel, role=None, registering=False):
        entry = self._state["agents"].get(agent, {})
        entry["agent"] = agent
        # Only room_join marks a name as an agent. People type into the web page
        # and never join, which is exactly how the room tells them apart.
        if registering:
            entry["is_agent"] = True
        entry["last_seen"] = now_iso()
        entry["last_seen_ts"] = time.time()
        if role:
            entry["role"] = role
        chans = set(entry.get("channels", []))
        chans.add(channel)
        entry["channels"] = sorted(chans)
        self._state["agents"][agent] = entry
        self._save_state_locked()

    def join(self, agent, channel, role=None):
        if not valid_name(agent):
            raise ValueError("agent name must be letters, numbers, dot, dash or underscore")
        if not valid_name(channel):
            raise ValueError("channel name must be letters, numbers, dot, dash or underscore")
        with self._lock:
            self._load_channel_locked(channel)
            if not os.path.exists(self._path(channel)):
                open(self._path(channel), "a").close()
            self._touch_locked(agent, channel, role, registering=True)

    def who(self, channel=None):
        cutoff = time.time() - PRESENCE_TTL
        with self._lock:
            out = []
            for entry in self._state["agents"].values():
                if entry.get("last_seen_ts", 0) < cutoff or not entry.get("is_agent"):
                    continue
                if channel and channel not in entry.get("channels", []):
                    continue
                out.append({
                    "agent": entry["agent"],
                    "role": entry.get("role"),
                    "channels": entry.get("channels", []),
                    "last_seen": entry.get("last_seen"),
                })
            return sorted(out, key=lambda e: e["agent"])

    def cursor(self, agent, channel, value=None):
        key = agent + "|" + channel
        with self._lock:
            if value is None:
                return int(self._state["cursors"].get(key, 0))
            if any(r['id'] == agent for r in self.delivery.sessions(channel)):
                offered = self._state.get('offered', {}).get(key, 0)
                if int(value) < 0 or int(value) > offered:
                    raise ValueError('cursor exceeds the complete page offered to this session')
            self._state["cursors"][key] = max(int(value), int(self._state["cursors"].get(key, 0)))
            self._save_state_locked()
            return self._state["cursors"][key]


STORE = None


def message_by_id(channel, message_id):
    with STORE._lock:
        return next((m for m in STORE._load_channel_locked(channel) if m['id'] == message_id), None)


def deliver_forever():
    while True:
        try:
            dispatch_one(STORE.delivery, message_by_id)
        except Exception:
            # Never log message text, credentials or host stderr.
            sys.stderr.write('room delivery dispatcher error; inspect delivery status\n')
        time.sleep(0.5)


# --------------------------------------------------------------------------
# HTTP layer: a small JSON API for the agents, and the web page for the human.
# --------------------------------------------------------------------------

TOKEN = os.environ.get("AGENT_ROOM_TOKEN", "").strip()
BIND = os.environ.get("AGENT_ROOM_BIND", "127.0.0.1")


class Handler(BaseHTTPRequestHandler):
    server_version = "AgentRoom/2.0"
    protocol_version = "HTTP/1.1"

    # quieter logs: one line per request, no noise
    def log_message(self, fmt, *args):
        if os.environ.get("AGENT_ROOM_VERBOSE"):
            sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    # ---- helpers ---------------------------------------------------------

    def _send(self, code, payload, ctype="application/json"):
        if isinstance(payload, (dict, list)):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        elif isinstance(payload, str):
            body = payload.encode("utf-8")
        else:
            body = payload
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _fail(self, code, message):
        self._send(code, {"error": message})

    def _authorised(self):
        if not TOKEN:
            return True
        header = self.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            return header[7:].strip() == TOKEN
        return self.headers.get("X-Room-Token", "").strip() == TOKEN

    def _body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return {}
        if length <= 0 or length > 2_000_000:
            return {}
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    # ---- routes ----------------------------------------------------------

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        def one(key, default=None):
            values = query.get(key)
            return values[0] if values else default

        if path in ("/", "/index.html"):
            return self._file("ui.html", "text/html; charset=utf-8")
        if path == "/icon.png":
            return self._file("icon.png", "image/png")
        if path == "/manifest.webmanifest":
            return self._send(200, {
                "name": "Agent Room", "short_name": "Room",
                "start_url": "/", "display": "standalone",
                "background_color": "#171815", "theme_color": "#171815",
                "icons": [{"src": "/icon.png", "sizes": "180x180", "type": "image/png"}],
            }, "application/manifest+json")
        if path == "/api/health":
            return self._send(200, {"ok": True, "home": ROOT, "version": "2.0", "delivery": "session-receipts", "pid": os.getpid()})

        if not self._authorised():
            return self._fail(401, "bad or missing room token")

        if path == "/api/channels":
            return self._send(200, {"channels": STORE.channels()})

        if path == "/api/messages":
            channel = one("channel", "")
            if not valid_name(channel):
                return self._fail(400, "channel required")
            since = int(one("since", "0") or 0)
            limit = max(1, min(500, int(one("limit", "200") or 200)))
            return self._send(200, {"messages": STORE.read(channel, since, limit, tail=one("tail") == "1")})

        if path == "/api/wait":
            channel = one("channel", "")
            if not valid_name(channel):
                return self._fail(400, "channel required")
            since = int(one("since", "0") or 0)
            timeout = float(one("timeout", "25") or 25)
            return self._send(200, {"messages": STORE.wait(channel, since, timeout)})

        if path in ('/api/sessions', '/api/delivery', '/api/inbox'):
            channel = one('channel', '')
            if not valid_name(channel):
                return self._fail(400, 'channel required')
            if path == '/api/sessions':
                return self._send(200, {'sessions': STORE.delivery.sessions(channel)})
            if path == '/api/delivery':
                return self._send(200, {'deliveries': STORE.delivery.status(channel, one('message'))})
            rows = STORE.delivery.inbox(one('session', ''), channel)
            return self._send(200, {'deliveries': [dict(r, message_content=message_by_id(channel, r['message'])) for r in rows]})

        if path == "/api/who":
            return self._send(200, {"agents": STORE.who(one("channel"))})

        if path == "/api/cursor":
            agent, channel = one("agent", ""), one("channel", "")
            if not (valid_name(agent) and valid_name(channel)):
                return self._fail(400, "agent and channel required")
            return self._send(200, {"cursor": STORE.cursor(agent, channel)})

        return self._fail(404, "no such endpoint")

    def do_POST(self):
        path = urlparse(self.path).path
        if not self._authorised():
            return self._fail(401, "bad or missing room token")
        data = self._body()

        try:
            if path in ('/api/register', '/api/ack', '/api/leave', '/api/channel-claim', '/api/channel-sent'):
                channel = data.get('channel', '')
                session = data.get('session', '')
                if not valid_name(channel) or not valid_name(session):
                    raise ValueError('valid channel and session required')
                if path == '/api/register':
                    if not valid_name(data.get('agent', '')):
                        raise ValueError('valid agent required')
                    result = STORE.delivery.register(session, channel, data['agent'], data.get('adapter', 'pull'), data.get('target', ''))
                elif path == '/api/ack':
                    result = STORE.delivery.ack(session, channel, data.get('delivery_ids', []))
                elif path == '/api/leave':
                    STORE.delivery.close(session, channel)
                    result = {'closed': True}
                elif path == '/api/channel-claim':
                    STORE.delivery.heartbeat(session, channel)
                    result = {'delivery': STORE.delivery.claim(session, channel, 'claude-channel')}
                    if result['delivery']:
                        r = result['delivery']
                        result['message'] = message_by_id(r['channel'], r['message'])
                else:
                    delivery_id = data.get('delivery_id')
                    if not any(r['id'] == delivery_id for r in STORE.delivery.inbox(session, channel)):
                        raise ValueError('delivery is not in this session/channel')
                    STORE.delivery.finish(delivery_id, 'submitted', 'channel event emitted; awaiting acknowledgement')
                    result = {'submitted': True}
                return self._send(200, result)
            if path == "/api/post":
                msg = STORE.post(
                    channel=str(data.get("channel", "")),
                    sender=str(data.get("from", "")),
                    text=str(data.get("text", "")),
                    to=data.get("to") or None,
                    kind=str(data.get("kind", "say")),
                    from_session=data.get('from_session'), to_session=data.get('to_session'),
                    request_id=data.get('request_id'),
                )
                return self._send(200, {"posted": msg, "delivery": STORE.delivery.status(msg["channel"], msg["id"])})

            if path == "/api/join":
                STORE.join(
                    agent=str(data.get("agent", "")),
                    channel=str(data.get("channel", "")),
                    role=data.get("role") or None,
                )
                return self._send(200, {"joined": True})

            if path == '/api/offer':
                agent, channel = data.get('session', ''), data.get('channel', '')
                if not valid_name(agent) or not valid_name(channel):
                    raise ValueError('session and channel required')
                value = int(data.get('through', 0))
                with STORE._lock:
                    messages = STORE._load_channel_locked(channel)
                    if value < 0 or value > len(messages):
                        raise ValueError('offered page exceeds channel')
                    key = agent + '|' + channel
                    offered = STORE._state.setdefault('offered', {})
                    offered[key] = max(value, offered.get(key, 0))
                    STORE._save_state_locked()
                return self._send(200, {'offered': value})

            if path == "/api/cursor":
                agent, channel = str(data.get("agent", "")), str(data.get("channel", ""))
                if not (valid_name(agent) and valid_name(channel)):
                    return self._fail(400, "agent and channel required")
                return self._send(200, {"cursor": STORE.cursor(agent, channel, int(data.get("cursor", 0)))})
        except (ValueError, TypeError, AttributeError) as exc:
            return self._fail(400, "invalid room request: " + str(exc))

        return self._fail(404, "no such endpoint")

    def _file(self, name, ctype):
        try:
            with open(os.path.join(HERE, name), "rb") as fh:
                return self._send(200, fh.read(), ctype)
        except OSError:
            return self._fail(500, "missing file: " + name)


def main():
    global STORE
    port = DEFAULT_PORT
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
    os.makedirs(ROOT, mode=0o700, exist_ok=True)
    owner = open(os.path.join(ROOT, 'daemon.lock'), 'a')
    try:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('another daemon owns this room data directory')
    # Bind before recovering or dispatching. An autostart collision must not
    # reinterpret a live send as crashed, or submit work from a second daemon.
    httpd = ThreadingHTTPServer((BIND, port), Handler)
    STORE = Store()
    threading.Thread(target=deliver_forever, daemon=True).start()
    httpd.daemon_threads = True
    sys.stderr.write("agent room listening on http://%s:%d  (messages in %s)\n" % (BIND, port, ROOT))
    sys.stderr.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
