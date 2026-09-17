# Claude app idle wake — takeover status, 2026-09-16

Taken over from the Codex `agent-room-claude-app-connection` task by the
opencode session (Martin's authorization). The candidate's Monitor code
(`8abfc91`, independent Astra review passed) was already installed; live
acceptance had never run and the room reset cleared the original binding.

## Verified with the installed binary this session

Binding `f1b9a94a-6450-46f5-82ac-828c61d4f50c` (pull, native
`9d34bace-2f77-4479-9d95-f44af9caba7e`) recreated; helper driven exactly as the
Claude app drives it (`CLAUDE_CODE_SESSION_ID` env, `--mcp --claude-app`):

1. `room_monitor_setup` (60s and 120s deadlines) returns the private socket
   command and timeout; `room_monitor_status` reports `connected: true` with
   honest scope note while a client is attached.
2. A targeted message posted through the room produced **one wake hint** on
   the Monitor socket within seconds: "Agent Room message available. …".
3. The instructed receiver flow completed through the same MCP tools:
   `room_read` returned the message, `room_ack` acknowledged delivery
   `b6d08d38b1a24ccea0c69cf3079d41eb`, `room_post` saved a reply.
4. Natural expiry at the deadline emitted the renewal hint:
   "Agent Room watch window ended. Renew with room_monitor_setup…".
5. MCP EOF closes its feed (socket removed) — verified; no stale sockets.

All test events, deliveries, receipts and offered cursors were removed
afterward; the room is clean with the three bindings registered (Claude app
pull, Codex builder, this opencode session).

## Remaining: the one native step

Everything the host must supply is proven except the native invocation itself:
in the Claude app conversation, the agent calls `room_monitor_setup` and starts
the returned command with the **Monitor tool** (timeout_ms from the result).
Then, while the conversation is idle, one targeted test message should be
answered by an actual read/ack/reply without any manual prompt. The Codex
acceptance plan (`work/monitor-acceptance-plan.md` in the connection task
directory) remains valid; its `monitor_acceptance.py` binding constant must be
updated to `f1b9a94a-6450-46f5-82ac-828c61d4f50c`.

Known limits, unchanged: watches expire after at most 30 minutes and need
renewal; no wake after app restart or device sleep unless re-proven; transport
connection is not receipt.