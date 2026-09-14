# Session delivery verification — 2026-09-14

Base: `94360c7`. Work isolated on `fix/session-delivery` in the agent-room
repository; no Iris source, runtime, calendar, mail, personal messages, or
credentials were accessed for testing. Shell commands ran **unconfined** under
the available execution policy. No app-wide automation/notification preferences
or Claude authentication settings were changed.

## Actual receiving agent

A separate existing Codex task explicitly agreed to receive synthetic probes.
The synthetic daemon used port 18787 and a separate data directory. Its normal
outbox dispatcher called the installed Codex queue command with the receiver's
verified exact UUID. Neither probe relied on sender polling as receipt evidence.

| Probe | Evidence |
|---|---|
| Idle | Receiver was idle before post. Message `90bf16b6e3f4` woke a new turn. Receiver reported full receipt without `room_read` or polling and acknowledged delivery `a821e7932756420ebddf5f496cf60c8e` via the isolated HTTP endpoint. |
| Busy | Receiver status was active when message `3066d70e38ab` was posted at 14:02:24Z. Its ongoing 40-second wait was not interrupted. It received the message in a new turn after finishing, and explicitly acknowledged `c024841b53f547289ddc1fce7a4a874c`. |

Both persisted receipts are `acknowledged`, with **one launch each**. The actual
receiver confirmed next-turn delivery, not mid-turn interruption. The receiver
used the new HTTP receipt endpoint because its existing loaded MCP connection
still had the old tool list. The automated transport suite separately exercises
the new `room_ack` MCP tool end to end.

## Claude limit

A standalone synthetic Claude Code 2.1.225 process was launched with a dedicated
MCP config, only synthetic room tools, no built-in tools, and the documented
custom channel flag. MCP connected, but the model returned `authentication_failed`:
its OAuth session had expired and could not refresh. No model tool turn ran and
no test event was sent to that process. No login repair was attempted. Therefore
**actual Claude receiving-agent acceptance remains unverified**. The connected
synthetic MCP client test proves notification framing and explicit receipt only.
Sonnet's existing session was not modified or restarted.

## Focused checks

`python3 -m unittest discover -s tests -v` passes 21 focused checks covering:

- startup health probe cannot re-enter daemon startup (A4);
- posts do not consume unread replies, 250 messages paginate oldest first,
  complete long messages are retained, cursors are separate and monotonic (A5);
- explicit read receipts reject cursor values beyond the offered page;
- exact UUID bindings, immutable routes, no name-based forwarding, room boundary;
- human-first delivery, closed sessions, wrong-session acknowledgement rejection;
- post idempotency, atomic claims, acknowledgement/send-completion race;
- restart recovery, bounded pre-launch retry, no replay of uncertain sends;
- a second daemon cannot open/recover/dispatch the same runtime store; stale
  Claude leases and lost in-flight sends become visibly unavailable/uncertain;
- actual HTTP authorization and stdio MCP read/post/ack round trips;
- a connected idle synthetic MCP client receives a Claude-format event without
  requesting a room read, acknowledges it, and receives no duplicate event.

The browser was inspected against synthetic data. Its exact session selector and
both acknowledged receipts rendered correctly. A synthetic post to a pull-only
session visibly showed `unavailable: pull only; recipient must read`.

## Repository and rollout limits

There is no repository or ancestor `AGENTS.md`, and no repository-mandated
independent review gate. Ownership and host/origin questions were posted through
the existing room to `opus@m1` (#174 and #175); no reply had arrived while this
candidate was being built. The primary checkout was clean when work started.
No conflicting edits were overwritten.

`git fetch origin` failed because this local repository has **no remotes**.
The coordinating task also checked 19 accessible GitHub repositories and found
none named agent-room. No remote or new repository was invented. Local commit is
possible; push needs a verified destination.

## Installed-service verification

The coordinator confirmed no known agent-room conflict and that the reversible
room-only installation was authorized. Main was rechecked clean at unchanged
94360c7; the room was reread for ownership/human messages and restart notice #176
was posted. Main fast-forwarded to 3a081eb; **only com.agentroom.daemon** restarted.
Health reported version 2.0 / session-receipts. The existing two channel journals
and state.json were byte-for-byte unchanged through the restart. A private data
backup and immutable old-source snapshot were retained outside Git. The old
94360c7 daemon successfully read a copy of the new synthetic journal/state,
confirming code rollback compatibility without restoring stale room data.

On the installed service (port 8787), the consenting receiving Codex task joined
with its exact UUID through the new bridge, posted synthetic message #1 in
`delivery-check-20260914`, and finished. Its state was confirmed idle. Reply #2
`c1874d951a4b` at 14:15:00Z started a new turn without any room read/poll. The
receiver acknowledged delivery `af66fec523c64670b3e42bce3752ad3a` through the installed
`room_ack` bridge. Stored status is acknowledged with exactly one attempt.
Both synthetic-channel registrations were closed afterward; the isolated test
daemon was stopped. The installed room remains running.

Existing app MCP processes do not refresh merely because their script changed.
A fresh bridge registration/receipt was verified, but existing loaded tool lists
were not silently upgraded. The installed CLI has no MCP reconnect command; its
app-server control proxy socket was unavailable. No new Codex daemon was started
and no global app settings were rewritten to work around this. Reconnect the
agent-room MCP connection in each app, or restart the app after current work,
then register each participating task explicitly as documented in README.

`opus@m1` was found in Claude Code's configured MCP entry. That is a configured
display identity, not proof of the active calendar session's host or session ID;
the ownership/host question remains unanswered. No route was guessed for it.
Do not describe the installed service or Codex acceptance as proof of Claude
receipt or automatic registration of other existing tasks.
