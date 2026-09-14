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
import threading
import uuid
from urllib.parse import urlencode
from delivery import prompt
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
URL = os.environ.get("AGENT_ROOM_URL", "http://127.0.0.1:8787").rstrip("/")
TOKEN = os.environ.get("AGENT_ROOM_TOKEN", "").strip()
AGENT = os.environ.get("AGENT_ROOM_AGENT", "").strip() or "unknown-agent"
CHANNEL = os.environ.get("AGENT_ROOM_CHANNEL", "").strip() or "general"
ROLE = os.environ.get("AGENT_ROOM_ROLE", "").strip()
AUTOSTART = os.environ.get("AGENT_ROOM_AUTOSTART", "1") != "0"
from urllib.parse import urlparse
IS_LOCAL = urlparse(URL).hostname in ('127.0.0.1', 'localhost', '::1')
SESSION = os.environ.get('AGENT_ROOM_SESSION') or os.environ.get('CODEX_THREAD_ID') or os.environ.get('CODEX_SESSION_ID') or str(uuid.uuid4())
ADAPTER = os.environ.get('AGENT_ROOM_ADAPTER', 'pull')
TARGET = os.environ.get('AGENT_ROOM_TARGET', '')
WRITE_LOCK = threading.Lock()
JOINED = set()
CHANNEL_ENABLED = os.environ.get('AGENT_ROOM_CLAUDE_CHANNEL') == '1'
if CHANNEL_ENABLED:
    ADAPTER = 'claude-channel'


PROTOCOL_DEFAULT = "2025-06-18"
KNOWN_PROTOCOLS = ("2024-11-05", "2025-03-26", "2025-06-18")


# --------------------------------------------------------------------------
# talking to the daemon
# --------------------------------------------------------------------------

def call(path, payload=None, timeout=None, recover=True):
    url = URL + path
    data = None
    headers = {"Accept": "application/json"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    last = None
    for attempt in range(3 if recover else 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout or 30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError:
            raise                      # the room answered and said no; that is an answer
        except Exception as exc:       # dropped connection, room restarting, not up yet
            last = exc
            if recover and attempt < 2:
                time.sleep(0.6 * (attempt + 1))
                ensure_daemon()
    raise last


def daemon_alive():
    try:
        call("/api/health", timeout=0.5, recover=False)
        return True
    except Exception:
        return False


def ensure_daemon():
    """Start the room on this machine if nothing is answering yet."""
    if daemon_alive():
        return True
    if not (AUTOSTART and IS_LOCAL):
        return False
    log_dir = os.environ.get("AGENT_ROOM_HOME", os.path.expanduser("~/.agent-room"))
    os.makedirs(log_dir, exist_ok=True)
    log = open(os.path.join(log_dir, "daemon.log"), "a")
    port = str(urlparse(URL).port or 8787)
    try:
        subprocess.Popen(
            [sys.executable, os.path.join(HERE, "roomd.py"), "--port", port],
            stdout=log, stderr=log, stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        log.close()
        return False
    log.close()
    for _ in range(8):
        time.sleep(0.25)
        if daemon_alive():
            return True
    return False


# --------------------------------------------------------------------------
# rendering messages for a model to read
# --------------------------------------------------------------------------

# Agents may write at length, so a read has to stay within something a reader
# can actually take in. Oldest complete messages win; explicit acknowledgement advances the page.
PER_READ_CHARS = 40000


def one(m):
    addressed = (' -> ' + m['to']) if m.get('to') else ''
    identity = ' (session %s)' % m['from_session'] if m.get('from_session') else ''
    return '#%d %s %s%s%s [%s]\n%s' % (m['seq'], m['at'], m['from'], identity, addressed, m.get('kind', 'say'), m['text'])


def page(messages):
    selected, size = [], 0
    for m in messages:
        block = one(m)
        if selected and size + len(block) > PER_READ_CHARS:
            break
        selected.append(m)
        size += len(block)
    return selected


def render(messages, empty='(nothing new)'):
    # Complete messages, oldest page first. Within that page the human comes first.
    return '\n\n'.join(one(m) for m in sorted(messages, key=lambda m: not m.get('human', False))) if messages else empty


def query(path, **args):
    return path + '?' + urlencode(args)


def read_page(channel, messages):
    selected = page(messages)
    result = render(selected)
    if selected:
        call('/api/offer', {'session': SESSION, 'channel': channel, 'through': selected[-1]['seq']})
        result += '\n\nUnread cursor unchanged. After reading ALL content, room_ack read_through=%d in channel %s. Read again for the next page.' % (selected[-1]['seq'], channel)
    return result


def channel_of(args):
    value = (args.get("channel") or "").strip()
    return value or CHANNEL


def cursor_get(channel):
    return int(call(query('/api/cursor', agent=SESSION, channel=channel))['cursor'])


def cursor_set(channel, value):
    return call('/api/cursor', {'agent': SESSION, 'channel': channel, 'cursor': int(value)})


# --------------------------------------------------------------------------
# the tools each agent sees
# --------------------------------------------------------------------------

TOOLS = [
    {
        "name": "room_join",
        "description": (
            "Register this exact receiving session and get the oldest unread page. Names are not task identities. "
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
                "text": {"type": "string", "description": "What you want to say. Use to_session from the message or room_sessions for delivery."},
                "to": {"type": "string", "description": "Participant display name only; this alone cannot select a receiving task. Use to_session for delivery."},
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
                "all": {"type": "boolean", "description": "Start at the beginning. Pages preserve complete messages; acknowledge each page then continue with a normal read."},
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


TOOLS[0]['inputSchema']['properties'].update({
    'session': {'type': 'string', 'description': 'Unique session identity; use your actual task UUID when known. Never a participant name.'},
    'adapter': {'type': 'string', 'enum': ['pull', 'codex-queue', 'claude-channel']},
    'target': {'type': 'string', 'description': 'For codex-queue only: this receiving task exact UUID on the daemon host. Explicit opt-in.'},
})
TOOLS[1]['inputSchema']['properties']['to_session'] = {'type': 'string', 'description': 'Exact recipient session from room_sessions. Required when participant name is ambiguous.'}
TOOLS.extend([
    {'name': 'room_sessions', 'description': 'List exact registered receiving sessions in this channel and their adapters. Names are not task identities.', 'inputSchema': {'type': 'object', 'properties': {'channel': {'type': 'string'}}}},
    {'name': 'room_inbox', 'description': 'Read this session delivery inbox, including unavailable/unconfirmed messages. Does not acknowledge.', 'inputSchema': {'type': 'object', 'properties': {'channel': {'type': 'string'}}}},
    {'name': 'room_ack', 'description': 'Explicit receipt ONLY after reading the complete messages. Posting and joining never acknowledge. read_through acknowledges a complete channel page; delivery_ids acknowledges pushed inbox messages.', 'inputSchema': {'type': 'object', 'properties': {'channel': {'type': 'string'}, 'session': {'type': 'string'}, 'read_through': {'type': 'integer'}, 'delivery_ids': {'type': 'array', 'items': {'type': 'string'}}}}},
    {'name': 'room_delivery', 'description': 'Show delivery states: submitted is not received; acknowledged means the receiving agent confirmed reading. Uncertain sends are not retried automatically.', 'inputSchema': {'type': 'object', 'properties': {'channel': {'type': 'string'}, 'message': {'type': 'string'}}}},
    {'name': 'room_leave', 'description': 'Unregister this session from this channel. Moving on to work does not require leaving; keep registered to receive replies.', 'inputSchema': {'type': 'object', 'properties': {'channel': {'type': 'string'}}}},
])


def run_tool(name, args):
    global SESSION, ADAPTER, TARGET
    channel = channel_of(args)

    if name == 'room_join':
        proposed = args.get('session') or SESSION
        if JOINED and proposed != SESSION:
            raise ValueError('this bridge is already bound to a session; use its identity')
        adapter = args.get('adapter', ADAPTER)
        target = args.get('target', TARGET)
        if adapter == 'claude-channel' and not CHANNEL_ENABLED:
            raise ValueError('Claude channel was not enabled when this bridge started')
        registration = call('/api/register', {'agent': AGENT, 'channel': channel, 'session': proposed, 'adapter': adapter, 'target': target})
        SESSION, ADAPTER, TARGET = proposed, adapter, target
        JOINED.add(channel)
        call('/api/join', {'agent': AGENT, 'channel': channel, 'role': args.get('role') or ROLE or None})
        messages = call(query('/api/messages', channel=channel, since=cursor_get(channel)))['messages']
        return 'You are %s. Session %s. %s\n\n%s' % (AGENT, SESSION, json.dumps(registration), read_page(channel, messages))

    if name == 'room_post':
        if channel not in JOINED:
            raise ValueError('join this channel before posting')
        result = call('/api/post', {
            'channel': channel, 'from': AGENT, 'text': args.get('text', ''),
            'to': args.get('to') or None, 'kind': args.get('kind') or 'say',
            'from_session': SESSION, 'to_session': args.get('to_session'), 'request_id': uuid.uuid4().hex,
        })
        return 'Posted #%d. Delivery: %s. Posting does not acknowledge unread replies.' % (result['posted']['seq'], json.dumps(result['delivery']))

    if name == 'room_read':
        since = 0 if args.get('all') else cursor_get(channel)
        messages = call(query('/api/messages', channel=channel, since=since))['messages']
        return read_page(channel, messages)

    if name == 'room_wait':
        timeout = max(1., min(float(args.get('timeout_s') or 15), 25.))
        messages = call(query('/api/wait', channel=channel, since=cursor_get(channel), timeout=timeout), timeout=timeout+2, recover=False)['messages']
        return read_page(channel, messages)

    if name == 'room_sessions':
        return json.dumps(call(query('/api/sessions', channel=channel)), indent=2)
    if name == 'room_delivery':
        return json.dumps(call(query('/api/delivery', channel=channel, **({'message': args['message']} if args.get('message') else {}))), indent=2)
    if name == 'room_inbox':
        rows = call(query('/api/inbox', channel=channel, session=SESSION))['deliveries']
        # Whole messages only; explicit receipts keep omitted records unread.
        selected, size = [], 0
        rows.sort(key=lambda r: not (r.get('message_content') or {}).get('human', False))
        for row in rows:
            block = json.dumps(row, ensure_ascii=False)
            if selected and size + len(block) > PER_READ_CHARS:
                break
            selected.append(row)
            size += len(block)
        return json.dumps({'session': SESSION, 'deliveries': selected, 'remaining': len(rows)-len(selected)}, ensure_ascii=False)
    if name == 'room_ack':
        if args.get('session', SESSION) != SESSION:
            raise ValueError('cannot acknowledge another session')
        cursor = cursor_set(channel, args['read_through']) if 'read_through' in args else None
        result = call('/api/ack', {'session': SESSION, 'channel': channel, 'delivery_ids': args.get('delivery_ids', [])})
        if cursor is not None:
            result['cursor'] = cursor
        return json.dumps(result)
    if name == 'room_leave':
        result = call('/api/leave', {'session': SESSION, 'channel': channel})
        JOINED.discard(channel)
        return json.dumps(result)

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
    with WRITE_LOCK:
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
            "capabilities": dict({"tools": {"listChanged": False}}, **({"experimental": {"claude/channel": {}}} if CHANNEL_ENABLED else {})),
            "serverInfo": {"name": "agent-room", "version": "2.0.0"},
            "instructions": (
                "A working room shared by agents from different apps, and by the person you work "
                "for, who reads it. You are '%s'; the channel is '%s'.\n"
                "Register your actual session with room_join. For Codex on the daemon host, use adapter=codex-queue and your exact task UUID for both session and target. Other hosts default to pull unless Claude channel delivery was enabled. Names are not session identities. Acknowledge only fully read content with room_ack. Incoming channel events require receipt. Moving on to work keeps your route registered. "
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


def channel_events():
    while True:
        for channel in list(JOINED):
            try:
                data = call('/api/channel-claim', {'session': SESSION, 'channel': channel}, recover=False)
                row = data.get('delivery')
                if row:
                    send({'jsonrpc': '2.0', 'method': 'notifications/claude/channel', 'params': {'content': prompt(row, data['message']), 'meta': {'channel': channel, 'session': SESSION, 'delivery_id': row['id']}}})
                    call('/api/channel-sent', {'session': SESSION, 'channel': channel, 'delivery_id': row['id']}, recover=False)
            except Exception:
                # Never retry a claimed event: a lost response may already be consumed.
                pass
        time.sleep(1)


def main():
    if CHANNEL_ENABLED:
        threading.Thread(target=channel_events, daemon=True).start()
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
