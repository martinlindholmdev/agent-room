#!/usr/bin/env python3
"""Agent Room bridge.

This is the piece each AI app connects to. It speaks MCP over stdin/stdout,
which every one of them understands, and forwards to the room daemon over
plain HTTP. Point it at another machine's daemon and the same agents are in
the same room across machines.

Zero dependencies: standard library only.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
URL = os.environ.get("AGENT_ROOM_URL", "http://127.0.0.1:8787").rstrip("/")
TOKEN = os.environ.get("AGENT_ROOM_TOKEN", "").strip()
AGENT = os.environ.get("AGENT_ROOM_AGENT", "").strip() or "unknown-agent"
CHANNEL = os.environ.get("AGENT_ROOM_CHANNEL", "").strip() or "general"
ROLE = os.environ.get("AGENT_ROOM_ROLE", "").strip()
AUTOSTART = os.environ.get("AGENT_ROOM_AUTOSTART", "1") != "0"
IS_LOCAL = URL.startswith("http://127.0.0.1") or URL.startswith("http://localhost")

PROTOCOL_DEFAULT = "2025-06-18"
KNOWN_PROTOCOLS = ("2024-11-05", "2025-03-26", "2025-06-18")


# --------------------------------------------------------------------------
# talking to the daemon
# --------------------------------------------------------------------------

def call(path, payload=None, timeout=None):
    url = URL + path
    data = None
    headers = {"Accept": "application/json"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout or 30) as response:
        return json.loads(response.read().decode("utf-8"))


def daemon_alive():
    try:
        call("/api/health", timeout=2)
        return True
    except Exception:
        return False


def ensure_daemon():
    """Start the room on this machine if nothing is answering yet."""
    if daemon_alive():
        return True
    if not (AUTOSTART and IS_LOCAL):
        return False
    log_dir = os.path.expanduser("~/.agent-room")
    os.makedirs(log_dir, exist_ok=True)
    log = open(os.path.join(log_dir, "daemon.log"), "a")
    port = URL.rsplit(":", 1)[-1]
    try:
        subprocess.Popen(
            [sys.executable, os.path.join(HERE, "roomd.py"), "--port", port],
            stdout=log, stderr=log, stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        return False
    for _ in range(40):
        time.sleep(0.25)
        if daemon_alive():
            return True
    return False


# --------------------------------------------------------------------------
# rendering messages for a model to read
# --------------------------------------------------------------------------

def render(messages, empty="(nothing new)"):
    if not messages:
        return empty
    lines = []
    for m in messages:
        who = m["from"]
        addressed = (" -> " + m["to"]) if m.get("to") else ""
        kind = m.get("kind", "say")
        tag = "" if kind == "say" else (" [" + kind + "]")
        lines.append("#%d  %s  %s%s%s\n%s" % (
            m["seq"], m["at"], who, addressed, tag, m["text"]))
    return "\n\n".join(lines)


def channel_of(args):
    value = (args.get("channel") or "").strip()
    return value or CHANNEL


def cursor_get(channel):
    try:
        return int(call("/api/cursor?agent=%s&channel=%s" % (AGENT, channel))["cursor"])
    except Exception:
        return 0


def cursor_set(channel, value):
    try:
        call("/api/cursor", {"agent": AGENT, "channel": channel, "cursor": int(value)})
    except Exception:
        pass


# --------------------------------------------------------------------------
# the tools each agent sees
# --------------------------------------------------------------------------

TOOLS = [
    {
        "name": "room_join",
        "description": (
            "Announce yourself in a room channel and get the recent conversation plus who else is here. "
            "Call this once at the start of a session before posting."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel": {"type": "string", "description": "Channel name. Defaults to this agent's configured channel."},
                "role": {"type": "string", "description": "One short line on what you are working on."},
            },
        },
    },
    {
        "name": "room_post",
        "description": (
            "Post to the channel so the other agents and the person you work for can see it. "
            "Use it to think out loud with another agent, plan, disagree, hand work over, claim "
            "a file, or answer a question you were asked. Address replies with 'to'."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "What you want to say."},
                "to": {"type": "string", "description": "Optional: the agent this is addressed to."},
                "kind": {"type": "string", "enum": ["say", "ask", "answer", "note", "decision", "status"],
                         "description": "What sort of message this is. Defaults to say."},
                "channel": {"type": "string"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "room_read",
        "description": (
            "Read what has been posted since you last looked. Worth doing before you touch files "
            "another agent might be holding. Reading does not oblige you to reply."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel": {"type": "string"},
                "all": {"type": "boolean", "description": "Read the whole channel from the beginning instead of only what is new."},
            },
        },
    },
    {
        "name": "room_wait",
        "description": (
            "Wait for the next message in the channel, up to a timeout in seconds (default 15, max 25). "
            "Returns as soon as anything is posted. Use it after asking another agent a question so you "
            "get the answer inside this same turn instead of guessing. The cap is deliberately short: a "
            "tool call that outlives the calling app's own request timeout is killed by the app, not by "
            "this room, and the agent sees a hard error instead of an answer. To wait longer, call it "
            "again -- consecutive short waits are equivalent to one long one and survive any client."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "timeout_s": {"type": "number", "description": "Seconds to wait. Default 15, maximum 25. Call again to keep waiting."},
                "channel": {"type": "string"},
            },
        },
    },
    {
        "name": "room_who",
        "description": "List the agents active in the room in the last 15 minutes, and what each said it is doing.",
        "inputSchema": {"type": "object", "properties": {"channel": {"type": "string"}}},
    },
    {
        "name": "room_channels",
        "description": "List the channels that exist, with how busy each one is.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def run_tool(name, args):
    channel = channel_of(args)

    if name == "room_join":
        call("/api/join", {"agent": AGENT, "channel": channel, "role": args.get("role") or ROLE or None})
        messages = call("/api/messages?channel=%s&limit=30" % channel)["messages"]
        who = call("/api/who?channel=%s" % channel)["agents"]
        if messages:
            cursor_set(channel, messages[-1]["seq"])
        roster = "\n".join(
            "  - %s%s" % (a["agent"], (" — " + a["role"]) if a.get("role") else "") for a in who
        ) or "  (you are the first one here)"
        return "You are %s in channel '%s'.\n\nHere now:\n%s\n\nRecent conversation:\n%s" % (
            AGENT, channel, roster, render(messages, "(the channel is empty)"))

    if name == "room_post":
        msg = call("/api/post", {
            "channel": channel, "from": AGENT, "text": args.get("text", ""),
            "to": args.get("to") or None, "kind": args.get("kind") or "say",
        })["posted"]
        cursor_set(channel, msg["seq"])
        return "Posted as #%d to '%s'." % (msg["seq"], channel)

    if name == "room_read":
        if args.get("all"):
            messages = call("/api/messages?channel=%s&limit=500" % channel)["messages"]
        else:
            since = cursor_get(channel)
            messages = call("/api/messages?channel=%s&since=%d" % (channel, since))["messages"]
        if messages:
            cursor_set(channel, messages[-1]["seq"])
        return render(messages)

    if name == "room_wait":
        # Capped well below the request timeout that MCP clients impose on a
        # tool call. A wait that outlives the client's own limit is killed by
        # the client, and the agent sees a hard protocol error rather than an
        # answer -- which is how a room that works looks broken. Short waits
        # chain: two calls of 15s wait 30s, and each one is safe on its own.
        timeout = float(args.get("timeout_s") or 15)
        timeout = max(1.0, min(timeout, 25.0))
        since = cursor_get(channel)
        # Only a small margin over the room's own deadline: the room returns on
        # time, so a longer margin here buys nothing and only pushes the call
        # closer to the client's limit.
        messages = call(
            "/api/wait?channel=%s&since=%d&timeout=%s" % (channel, since, timeout),
            timeout=timeout + 5,
        )["messages"]
        if messages:
            cursor_set(channel, messages[-1]["seq"])
            return render(messages)
        return ("Nothing was posted within %.0f seconds. This is a normal empty wait, not an "
                "error -- call room_wait again to keep listening, or carry on with your work." % timeout)

    if name == "room_who":
        who = call("/api/who?channel=%s" % channel)["agents"]
        if not who:
            return "Nobody has been active in the last 15 minutes."
        return "\n".join(
            "%s%s  (last seen %s)" % (a["agent"], (" — " + a["role"]) if a.get("role") else "", a["last_seen"])
            for a in who)

    if name == "room_channels":
        rows = call("/api/channels")["channels"]
        if not rows:
            return "No channels yet. Posting to one creates it."
        return "\n".join(
            "%-24s %4d messages   last: %s" % (r["channel"], r["messages"], r["last_at"] or "-")
            for r in rows)

    raise ValueError("unknown tool: " + name)


# --------------------------------------------------------------------------
# MCP over stdin/stdout
# --------------------------------------------------------------------------

def send(message):
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def reply(request_id, result):
    send({"jsonrpc": "2.0", "id": request_id, "result": result})


def error(request_id, code, message):
    send({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}})


def handle(request):
    method = request.get("method")
    request_id = request.get("id")
    params = request.get("params") or {}

    if method == "initialize":
        asked = params.get("protocolVersion")
        version = asked if asked in KNOWN_PROTOCOLS else PROTOCOL_DEFAULT
        ensure_daemon()
        return reply(request_id, {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "agent-room", "version": "1.0.0"},
            "instructions": (
                "A working room shared by agents from different apps, and by the person you work "
                "for, who reads it. You are '%s'; the channel is '%s'.\n"
                "Discuss properly here: plan, challenge each other, argue a design out, hand work "
                "over, say what you are taking and what you have released. Take the space you "
                "need to make the argument.\n"
                "One rule that outranks the rest: a message from the person you work for comes "
                "first. Stop what you are doing, answer it directly and in plain language, and "
                "address it to them by name. Never leave them waiting while you finish a point "
                "with another agent, and never discuss them in the third person."
                % (AGENT, CHANNEL)),
        })

    if method in ("notifications/initialized", "notifications/cancelled"):
        return
    if method == "ping":
        return reply(request_id, {})
    if method == "tools/list":
        return reply(request_id, {"tools": TOOLS})

    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments") or {}
        try:
            if not ensure_daemon():
                raise RuntimeError(
                    "the room is not running and could not be started. "
                    "Start it by hand, or check ~/.agent-room/daemon.log")
            text = run_tool(name, args)
            return reply(request_id, {"content": [{"type": "text", "text": text}], "isError": False})
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            return reply(request_id, {"content": [{"type": "text", "text": "Room refused that: " + detail}], "isError": True})
        except Exception as exc:
            return reply(request_id, {"content": [{"type": "text", "text": "Room error: %s" % exc}], "isError": True})

    if request_id is not None:
        return error(request_id, -32601, "method not found: %s" % method)


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except ValueError:
            continue
        if isinstance(request, list):
            for item in request:
                handle(item)
        else:
            handle(request)


if __name__ == "__main__":
    main()
