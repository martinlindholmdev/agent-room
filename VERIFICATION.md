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

Actual running room processes and existing MCP clients require a coordinated
upgrade/reconnect before these changes apply to them. See README for setup and
limits; source implementation and synthetic acceptance must not be described as
proof that every existing agent session has been upgraded.
