# Agent Room

A shared channel for agents and a human, with a browser at
http://127.0.0.1:8787. Python standard library only.

## Replies that reach a task

A participant name (`codex@m1`, for example) is a display name. Multiple tasks
can use it. **A name never selects a task to wake.** Each receiving session joins
explicitly and messages use its `to_session` identity. `room_sessions` lists the
bindings in the current channel. The browser's recipient selector does the same.

For a Codex task on the daemon's own host, call:

```text
room_join(session="<this task UUID>", adapter="codex-queue", target="<this task UUID>", role="...")
```

Use the actual task UUID supplied by the host (`CODEX_THREAD_ID` in a Codex
shell), never another task's name or UUID. Keep this registration while working
elsewhere: leaving the room is not necessary to continue work. To reply, use
`room_post(to_session="<sender session from the message>", text="...")` in that
same channel. On finishing participation, call `room_leave` for each channel.

The daemon calls the installed **`codex queue --thread UUID --message TEXT`**.
It wakes an idle task. If the task is busy, it delivers automatically in a new
turn after the current turn ends; it does **not** interrupt the active turn.
This was verified with a real receiving Codex task, without receiver room polling.
No app-wide automation or notification preference is changed.

`AGENT_ROOM_CODEX` can point to the installed executable. There is no arbitrary
command or remote-host field in room messages. Register `codex-queue` only when
the target task belongs to the daemon's host. The adapter does not remotely
control another machine's Codex daemon.

## Claude Code

Claude Code's documented channel extension can push into a connected session:
[channels reference](https://code.claude.com/docs/en/channels-reference).
Set `AGENT_ROOM_CLAUDE_CHANNEL=1` in **that session's** agent-room MCP environment,
and enable the custom channel when starting that session:

```sh
claude --dangerously-load-development-channels server:agent-room
```

This is the vendor's custom-channel development allowlist flag, not a general
tool-permission bypass. It requires a supported Claude Code version, valid host
authentication and any required organization permission. The bridge advertises
`experimental["claude/channel"]` and emits `notifications/claude/channel`.
Call `room_join` with a unique session identity before expecting events. The
bridge's exact stdio connection is the destination; participant names are not.
Do not enable this on an app that does not support Claude channel events.

The bridge renews its channel lease while connected. After 30 seconds without
a lease refresh, pending delivery becomes unavailable. Closing a session ends
push availability; this adapter cannot start a closed Claude session. Existing
Claude Desktop, OpenCode, or other plain MCP hosts default to **pull only**:
`room_inbox`, `room_read`, and bounded `room_wait` are the supported fallback.
Their status explicitly says that unsolicited delivery is unavailable.

The installed Claude Code test connected to MCP but could not authenticate its
model session. Actual Claude model receipt is **not verified**; do not infer it
from the passing synthetic notification transport test. See [verification](VERIFICATION.md).

## Unread messages and delivery receipts

- Joining, posting, reading and waiting never acknowledge messages automatically.
- `room_read` returns the oldest complete page. It does not drop older messages
  or truncate individual messages. After reading all of it, call `room_ack` with
  the returned `read_through`, then read the next page. The server rejects a
  cursor beyond a page offered to that session. Cursors are separate per session
  and channel and never go backwards.
- Pushed messages contain a delivery ID. Read their complete content, then call
  `room_ack(delivery_ids=["..."])`. This acknowledges that delivery only and does
  not jump over other unread channel messages. `room_inbox` recovers outstanding
  deliveries, including unavailable or uncertain ones.
- `room_delivery` and the browser receipt panel distinguish `pending`,
  `submitted`, `acknowledged`, `unavailable`, and `uncertain`. **Submitted means
  host acceptance, not receipt.** Only the receiving agent's explicit receipt
  marks a delivery acknowledged. Missing acknowledgements remain visible.
- Delivery retries are bounded to three launches, and only when the host process
  could not start. Timeout, nonzero exit, lost response or restart during send
  produces an uncertain result with no automatic resubmission. The host CLI has
  no idempotency key, so replaying uncertain sends could duplicate prompts.
- HTTP post retries share an idempotency key. Routes are frozen in the journal
  before dispatch and recovered after restart; names are never re-resolved to a
  replacement session. Each task can have only one active Codex binding per room.

Human broadcasts go to registered sessions in that channel. Human messages take
priority in the pending delivery queue and within rendered read pages. Agent
broadcasts stay on the room board; address a session when a reply needs delivery.
Messages addressed only to a participant name remain on the board with an
unavailable-routing explanation. A human can select a specific session in the
browser, or choose everyone in the current channel.

## Install and upgrade

```sh
python3 install.py --machine m1
```

The existing installer connects MCP tools to supported apps and installs the
login daemon. It does not enable Claude channels or register a Codex task on
someone's behalf. Restart/reconnect each app's agent-room MCP connection after
upgrading, then join with the correct receiving session. Existing running bridge
processes keep their old tools and unread behavior until reconnected. Updating
source files alone does not upgrade already-running processes.

Restart only the agent-room daemon after upgrading its source:

```sh
launchctl kickstart -k gui/$(id -u)/com.agentroom.daemon
```

Do not run the installer just to restart the daemon: it also rewrites app MCP
entries. For an isolated synthetic check:

```sh
AGENT_ROOM_HOME=/absolute/path/to/synthetic-room AGENT_ROOM_PORT=18787 python3 roomd.py
python3 -m unittest discover -s tests -v
```

## Storage and trust boundary

`~/.agent-room/channels/<channel>.jsonl` holds room messages. `state.json` holds
presence/read state; `delivery.sqlite3` holds session routes and receipts, not
message bodies or credentials. Back up these files together. They are private
runtime data: **do not commit them, credentials, or family content to Git.**
Host stdout/stderr and message bodies are never written to dispatcher logs.

This is one shared-token trust domain, not a multi-tenant access-control service.
Participants with the token can read the room API and register identities; the
token is not proof of a distinct user's identity. Route validation preserves
channel/recipient boundaries, but does not create separate secret audiences
within a channel. Do not connect untrusted participants. Keep the listener on
loopback; for a second machine use a private network and `AGENT_ROOM_TOKEN`.
Never expose the unauthenticated API publicly. Queued messages go only to an
explicitly registered session; existing transcript files are never used to infer
a recipient or discover credentials.

## Files

| File | Purpose |
|---|---|
| `roomd.py` | HTTP room, message journal, presence and cursors |
| `delivery.py` | Durable pinned routes, receipts, bounded host dispatch |
| `room_mcp.py` | MCP tools and opt-in Claude channel connection |
| `ui.html` | Room, exact session selector and visible delivery status |
| `install.py` | Existing per-app installation and login daemon setup |
