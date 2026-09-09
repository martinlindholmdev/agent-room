#!/usr/bin/env python3
"""Agent Room daemon.

A tiny message bus so AI agents from different vendors can talk to each other,
plus a web page a human can watch and join from.

Zero dependencies: standard library only, runs on the Python that ships with
macOS. Messages are stored as plain JSON lines on disk so they stay readable
without this program.
"""

import json
import os
import re
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("AGENT_ROOM_HOME", os.path.expanduser("~/.agent-room"))
CHANNELS = os.path.join(ROOT, "channels")
STATE_PATH = os.path.join(ROOT, "state.json")
DEFAULT_PORT = int(os.environ.get("AGENT_ROOM_PORT", "8787"))

NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._@-]{0,63}$")
PRESENCE_TTL = 15 * 60          # an agent is "here" for 15 min after activity
# A coordination channel is not a place for essays. Agents get a short line;
# the long allowance exists only for answering a person who asked a question.
MAX_AGENT_TEXT = 350
MAX_HUMAN_TEXT = 2000
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

    def post(self, channel, sender, text, to=None, kind="say"):
        if not valid_name(channel):
            raise ValueError("channel name must be letters, numbers, dot, dash or underscore")
        if not valid_name(sender):
            raise ValueError("agent name must be letters, numbers, dot, dash or underscore")
        text = (text or "").strip()
        if not text:
            raise ValueError("message text is empty")
        # Anyone who registered through room_join is an agent. Whoever the web
        # page is used by never registers, so a message addressed to them is a
        # reply to a person and may run long.
        to_person = bool(to) and not self._state["agents"].get(to, {}).get("is_agent")
        limit = MAX_HUMAN_TEXT if to_person else MAX_AGENT_TEXT
        if len(text) > limit:
            raise ValueError(
                "message is %d characters; the limit is %d. Say it in one or two "
                "lines. The room is for claims, handoffs, blockers and answers — "
                "not for discussion." % (len(text), limit))
        if kind not in KINDS:
            kind = "say"
        with self._cond:
            msgs = self._load_channel_locked(channel)
            msg = {
                "seq": len(msgs) + 1,
                "id": uuid.uuid4().hex[:12],
                "at": now_iso(),
                "channel": channel,
                "from": sender,
                "to": to if (to and valid_name(to)) else None,
                "kind": kind,
                "text": text,
            }
            with open(self._path(channel), "a") as fh:
                fh.write(json.dumps(msg, ensure_ascii=False) + "\n")
            msgs.append(msg)
            self._touch_locked(sender, channel)
            self._cond.notify_all()
            return msg

    def read(self, channel, since=0, limit=200):
        with self._lock:
            msgs = self._load_channel_locked(channel)
            out = [m for m in msgs if m["seq"] > since]
            return out[-limit:] if limit else out

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
                    return fresh
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
            self._state["cursors"][key] = int(value)
            self._save_state_locked()
            return int(value)


STORE = Store()


# --------------------------------------------------------------------------
# HTTP layer: a small JSON API for the agents, and the web page for the human.
# --------------------------------------------------------------------------

TOKEN = os.environ.get("AGENT_ROOM_TOKEN", "").strip()
BIND = os.environ.get("AGENT_ROOM_BIND", "127.0.0.1")


class Handler(BaseHTTPRequestHandler):
    server_version = "AgentRoom/1.0"
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
            return json.loads(self.rfile.read(length).decode("utf-8"))
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
            return self._send(200, {"ok": True, "home": ROOT, "version": "1.0"})

        if not self._authorised():
            return self._fail(401, "bad or missing room token")

        if path == "/api/channels":
            return self._send(200, {"channels": STORE.channels()})

        if path == "/api/messages":
            channel = one("channel", "")
            if not valid_name(channel):
                return self._fail(400, "channel required")
            since = int(one("since", "0") or 0)
            limit = int(one("limit", "200") or 200)
            return self._send(200, {"messages": STORE.read(channel, since, limit)})

        if path == "/api/wait":
            channel = one("channel", "")
            if not valid_name(channel):
                return self._fail(400, "channel required")
            since = int(one("since", "0") or 0)
            timeout = float(one("timeout", "25") or 25)
            return self._send(200, {"messages": STORE.wait(channel, since, timeout)})

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
            if path == "/api/post":
                msg = STORE.post(
                    channel=str(data.get("channel", "")),
                    sender=str(data.get("from", "")),
                    text=str(data.get("text", "")),
                    to=data.get("to") or None,
                    kind=str(data.get("kind", "say")),
                )
                return self._send(200, {"posted": msg})

            if path == "/api/join":
                STORE.join(
                    agent=str(data.get("agent", "")),
                    channel=str(data.get("channel", "")),
                    role=data.get("role") or None,
                )
                return self._send(200, {"joined": True})

            if path == "/api/cursor":
                agent, channel = str(data.get("agent", "")), str(data.get("channel", ""))
                if not (valid_name(agent) and valid_name(channel)):
                    return self._fail(400, "agent and channel required")
                return self._send(200, {"cursor": STORE.cursor(agent, channel, int(data.get("cursor", 0)))})
        except ValueError as exc:
            return self._fail(400, str(exc))

        return self._fail(404, "no such endpoint")

    def _file(self, name, ctype):
        try:
            with open(os.path.join(HERE, name), "rb") as fh:
                return self._send(200, fh.read(), ctype)
        except OSError:
            return self._fail(500, "missing file: " + name)


def main():
    port = DEFAULT_PORT
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
    httpd = ThreadingHTTPServer((BIND, port), Handler)
    httpd.daemon_threads = True
    sys.stderr.write("agent room listening on http://%s:%d  (messages in %s)\n" % (BIND, port, ROOT))
    sys.stderr.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
