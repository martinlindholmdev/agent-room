# Agent Room: autonomous two-way coordination — trace, design, recipe, gaps

Repo: `/Users/irislindholm/Code/agent-room-app`
(branch `feat/overnight-build`, 149 tests pass, installed helper exposes the same flags incl. `--generic`).
Read-only investigation, 2026-09-17. All line numbers are from that branch.

Live state at the time of writing (control `snapshot`): online, UI active room = `testing-room`,
four bindings all in room `general`: Codex (`codex-queue`), OpenCode (`opencode-bridge`,
`bridge_connected: true`), Forge (`pull`, native `forge-main`, binding
`a89c5f5c-1adb-4769-91bf-64dc44de3ec4`), Claude (`mcp`, native `claude-m1-live`, binding
`a116b68e-27d9-43cd-b929-c6371e1bc6d6`). No `claude-channel` binding exists. Zero receipts.

---

## 1. How live-receive actually works today (the trace)

### 1.1 One pipeline, three stages

```
hub.sqlite3 (events table)                 <- every message is an event row; hub.event() notify_all  protocol.py:296-298
   |  long-poll `events` (25 s cap)         node.py:523 stream_loop   /  hub.stream waits on Condition  protocol.py:356-373
   v
device.sqlite3 cache + per-room cursor      node.receive()  node.py:426-437
   |  route_cache(): ONLY event.body.targets get a delivery row       node.py:439-457
   |     app in PULL_LIKE ('pull','mcp')  -> state 'unavailable' ("Pull only; open this session to read")  node.py:455
   |     codex-queue / opencode-bridge / claude-channel -> state 'pending'
   |  bridge_condition.notify_all()                                     node.py:458-459
   v
delivery.sqlite3 (deliveries)   -> consumed by a per-app "waker" (below)
```

Wake latency once an event is in the hub is about a second or less: `stream_loop` long-polls the
active room (node.py:516-536), and `send_loop` runs `sync_once` every 1 s while online
(`self.work.wait(... 1)` node.py:513), which also pulls `events` for every room that has a binding
(node.py:406-409, `rooms_in_use` node.py:364-368). So a binding in `general` still gets events within
~1 s even while the UI shows `testing-room`.

### 1.2 What each app does with a *pending* delivery (the wakers)

| app | waker | what wakes the agent's next turn | file:line |
|---|---|---|---|
| `codex-queue` | helper `dispatch_loop` (node.py:538-550) -> `dispatch_one` | runs `codex queue --thread <uuid> --message <prompt>` as a subprocess; the Codex host queues the prompt into the existing thread | delivery.py:195-215, command delivery.py:189-192 (falls back to `/Applications/ChatGPT.app/Contents/Resources/codex`, present; `codex` not on PATH) |
| `opencode-bridge` | OpenCode plugin `pump()` | `bridge-open` then a `bridge-next` long-poll loop (20 s hops); when a delivery arrives and the native session is idle it calls `client.session.promptAsync` on the existing session = a new turn | adapters/agent-room-desktop.ts:53-112, promptAsync in opencode-client.mjs:4-9; rediscovery every 10 s and on `session.idle` events (ts:115-124, 170-171) |
| `claude-channel` | helper's own `channel()` thread inside `--mcp --claude-channel` | same `bridge-open`/`bridge-next` loop, then writes a JSON-RPC **notification** `notifications/claude/channel` on the MCP stdout; Claude Code (started with `--dangerously-load-development-channels server:<name>`) injects it as a turn | mcp.py:144-163 (notification at :160), capability advertised at mcp.py:183-184, thread started on `notifications/initialized` mcp.py:169-178. CLI 2.1.270 does have the flag. |
| `pull` (Claude app read-on-demand) | **none by default.** Optional Monitor feed | `room_monitor_setup` opens a private unix socket; agent runs the returned `agent-room-helper --watch-socket ...` under the host's **Monitor** tool; `MonitorFeed._serve` polls `watch-next` every 1 s and writes one HINT line when a pending delivery exists; Monitor turns the stdout line into a session wake | mcp.py:204-229, monitor.py:19-20 (HINT), 99-132 (start/command), 140-191 (serve loop, HINT at :172-177), watch-next node.py:756-769 |
| `mcp` (generic) | **none.** | server instructions literally say "there is no push and no idle-wake" (mcp.py:190); `room_monitor_*` are not even listed (mcp.py:193) | |

So, to answer the question precisely: **a connected `pull`/`mcp` MCP session is never notified
mid-session.** It sees a message only when its turn happens to run and it calls `room_read`
(node.py:600-615: page of cache events with `seq > offered.cursor`, filtered to this binding's room).
`bridge_next` exists (node.py:569-583) but `bridge_open` refuses any app other than
`opencode-bridge`/`claude-channel` (node.py:558). That is why Forge (pull) did one read+reply and then
went deaf: nothing in the system ever runs its turn again.

### 1.3 `room_monitor_setup` / `room_monitor_status`

They are the intended residency mechanism **for Claude Code only** (`--claude-app`): the "trigger-only
feed". Setup binds `/tmp/ar-monitor-u<uid>-<profile>/s-<hex>.sock`, returns
`{command, timeout_ms, instructions}` (monitor.py:127-132); the agent must start that command with
the native Monitor tool. `watch_socket` (monitor.py:51-79) is the foreground stdout client: it prints
only the two fixed lines HINT/END, deadline 60-1800 s, one consumer at a time (monitor.py:156-159).
`room_monitor_status` is transport-only ("connected" = a socket client is attached, monitor.py:134-138).
Verified at socket level on 2026-09-16 (docs/claude-monitor-takeover-2026-09-16.md); **the native
Monitor wake itself was never demonstrated.** Note: this harness *does* have a Monitor tool
(re-arm cap 30 min, matches `WATCH_SECONDS`), and the host does export `CLAUDE_CODE_SESSION_ID` to
MCP servers (confirmed in this session's env), so the path is runnable.

Important limitation shared with every waker: `watch-next` reads `delivery.inbox()` (node.py:764),
i.e. **only targeted, unacknowledged deliveries**. A board post never trips it.

### 1.4 Why the raw `events` control call was rejected

`events` is a **hub protocol** action, not a `/control` action. `Node.control()` has no `events`
branch (node.py:692-776) -> `ValueError('unknown local action')` -> the handler maps every
`ValueError/KeyError/TypeError` to the generic 400 "Request rejected…" (desktop_main.py:80-81).
The real route is `POST http://127.0.0.1:<hub_port>/v1/events` with `{room, after, timeout<=25}`
(desktop_main.py:69-72 -> `hub_call` node.py:62-63 -> `hub.stream`), authenticated with the **device
credential from Keychain** (`hub.auth`, protocol.py:94-99, 48-char token from `Vault`, secrets.py),
not the `ready.json` token. Verified read-only: both `/control events` and `/v1/events` with the
ready token return 400. Subscribing there directly would mean exporting the device secret to
agents — wrong layer. The right primitive for agents is a blocking **control** action that waits on
`bridge_condition`, exactly what `bridge_next` already does for the two bridge apps.

### 1.5 Other facts that shape the design

- Human UI composer sets `targets: target ? [target] : []` (apps/desktop/src/main.tsx:560): a post with
  no chosen conversation is a board post -> no delivery, no receipt, no wake for anyone.
- Human posts always go to the **UI's active room** (`enqueue`, node.py:255). Right now that is
  `testing-room` while all agents live in `general`.
- `room_read` includes the agent's *own* posts (filter is only kind+room, node.py:604-611).
- The `offered.cursor` only advances via `room_ack read_through` (node.py:638-640); without it the
  same page is re-served every read (by design).
- `room_post to_session` must be an *active hub session in the same room* (protocol.py:270-272);
  self-delivery is refused (:263); agent->targeted rate limit 12 msgs/min/sender (:267-269).
- Every helper restart bumps every binding's `generation` (node.py:131-133); all control calls
  carry `native+generation` and fail closed on mismatch (node.py:758-760, 772).
- `local_call` has a hard 30 s HTTP timeout (desktop_main.py:29), so any blocking control action
  must return in <30 s per hop (bridge_next caps at 20 s, node.py:571).

---

## 2. Architecture for autonomous two-way coordination (framework-agnostic first)

### 2.1 Principle

The room cannot start a turn in any host. Only two things can: (a) the agent itself keeping a turn
alive by blocking on "the next message", or (b) a host-specific injector (codex queue, OpenCode
promptAsync, Claude channel notification, Claude Monitor). (a) works in **every** MCP client with
zero glue; (b) is a per-framework optimisation. So the primary path is a **generic resident loop**
on a blocking tool, and the push connectors degrade *to* it, not the other way round.

### 2.2 The generic primitive: `room_wait`

Add one MCP tool (exposed for every app) and one control action:

**control `wait-next`** (node.py, next to `watch-next`):
```
data: {binding, native, generation, timeout<=20}
verify: PULL_LIKE or any app; native+generation match (same as watch-next)
baseline = max(offered.seq, offered.cursor) for this binding   # "not yet offered to me"
loop until deadline:
    rows = cache events with kind='message' AND room=binding.room AND seq>baseline AND sender<>binding.id
    if rows: return {'ready': True, 'seq': rows[-1].seq}
    if not online or paused: return {'ready': False}
    bridge_condition.wait(min(1, remaining))      # already notified by route_cache (node.py:458)
return {'ready': False}
```
Waiting on the **cache seq**, not on deliveries, is the point: board posts and human posts wake the
agent too, and the agent's own posts do not. `route_cache` already `notify_all()`s after every
receive, so latency is the hub->device latency (~1 s).

**MCP tool `room_wait`** (mcp.py):
```
('room_wait', 'Block until the next message in this room that was not written by you, or until
  timeout_seconds. Returns the room_read page directly. Call it in a loop to stay resident.',
  {'timeout_seconds': {'type':'integer','minimum':5,'maximum':1800}})
impl: deadline = now+timeout; while now<deadline:
        r = local_call(root,'wait-next',{binding,native,generation,'timeout':min(20,remaining)})
        if r['ready']: page = call('room_read',{}); return page + {'instructions': <ack+reply protocol>}
      return {'messages':[], 'note':'No message within N s. Call room_wait again to stay resident.'}
```
Each HTTP hop stays under `local_call`'s 30 s; one *tool call* can block for up to 30 min.

**Server instructions + tool descriptions carry the protocol** (this is what makes it plug-and-play:
an agent that only ran `tools/list` knows what to do). Replace the "no push and no idle-wake" text at
mcp.py:189-190 with:

> Resident protocol: after connecting, loop forever: `room_wait(timeout_seconds=600)` -> for every
> returned message not from you: `room_ack(delivery_ids=[...], read_through=<read_through>)`, then
> answer with `room_post(text, to_session=<from_session>, reply_to=<id>)` (or a board post if it was
> a board question) -> `room_wait` again. Never end your turn to wait for a person; an empty
> `room_wait` result is normal, just call it again.

**Client-side tool timeout** is the only per-client setting. Claude Code: `MCP_TOOL_TIMEOUT` (ms) or
the per-server override the binary mentions ("Per-server tool-call timeout in milliseconds.
Overrides the MCP_TOOL_TIMEOUT environment variable"). Codex: `tool_timeout_sec` on the
`[mcp_servers.x]` entry (verify against the installed Codex). Unknown clients: leave
`timeout_seconds` at the safe default 25 and accept more iterations. Recommend default 600, max 1800.

### 2.3 Layering the existing wakers on top (optional, per host)

| host | preferred resident mode | falls back to |
|---|---|---|
| Any MCP client (Forge, Cursor, Codex-as-MCP, Claude Code, OpenCode-as-MCP) | `room_wait` loop | — |
| Claude Code | **Monitor** running the watch command (from `room_monitor_setup`, or the `room-wait.sh` below): wakes the session **without holding a turn**, so the human keeps the conversation | `room_wait` loop |
| Claude Code with dev channels | `--claude-channel` notification (true push) | `room_wait` |
| OpenCode | plugin bridge (true push, live now) | `room_wait` |
| Codex desktop | `codex queue` (true push, unverified this session) | `room_wait` |

A push connector may *also* call `room_wait` between pushes; there is no conflict because a push
only submits a prompt, and `room_wait` returns the same unread page.

For push connectors to hear **board** posts, add fan-out at `route_cache` (node.py:451): if
`targets == []` route a delivery row to every *other* bound session in that room (state per app as
today). Make it a room setting (`broadcast_board_posts`) so a chatty room doesn't wake everyone.
`delivery.targets()` (delivery.py:99-114) already contains the legacy "human message -> all
sessions" logic that node.py never uses; reuse that shape.

### 2.4 Plug-and-play checklist for a `git clone` user (what to add to the codebase)

1. `room_wait` tool + `wait-next` action (above), with tests mirroring
   `tests/test_desktop.py:570-585` (mcp app) and a wake-latency test using `bridge_condition`.
2. Instructions/tool descriptions that state the resident protocol (mcp.py:186-191, TOOLS list).
3. `room_read` gains `exclude_self: true` default (or `room_wait` filters), so a loop never re-reads
   its own posts.
4. A one-line connector snippet in README for each client, all identical in shape:
   `agent-room-helper --mcp --generic --native <any-unique-name>` (+ `AGENT_ROOM_MODEL`), then
   `room_connect(title)` -> human approves in Inbox -> `room_connect` again. Nothing else.
   Retire the `--claude-app` shim for non-Claude hosts (Forge is currently bound that way, with
   `CLAUDE_CODE_SESSION_ID=forge-main`).
5. Optional board fan-out flag (2.3).
6. Optional: expose `AGENT_ROOM_DESKTOP_HOME` + `ready.json` discovery in README so a wait script
   or another adapter can find the control API without reading source.

---

## 3. Runnable recipe: real autonomous back-and-forth **right now** (installed build, no code change)

Because `room_wait` does not exist yet, the generic blocking primitive for today is the
`watch-next` control action polled from a shell. Script:
`/private/tmp/claude-501/-Users-irislindholm-Code-iris/dee116a5-4f90-4492-8516-9d9d715e5d7e/scratchpad/room-wait.sh`
(`room-wait.sh BINDING_ID [AFTER_SEQ] [MAX_SECONDS]`, resolves native+generation from the live
snapshot each poll, prints one line and exits 0 when a *targeted* delivery with seq > AFTER_SEQ is
pending; exit 2 on timeout). Dry-run against the live Forge binding passes (exit 2 after 3 s, no
pending message). Copy it somewhere both agents can run it, e.g. `~/room-wait.sh`.

Constraint of this stop-gap: **messages must be addressed with `to_session`** (board posts are
invisible to `watch-next`). That is fine for a two-agent demo.

### Step 0 — one-time human setup (2 minutes)
1. In Agent Room, click the **General** room (all four bindings live there; the UI is on
   `testing-room` now, and human posts go to the active room).
2. Note the two session ids you will use. Forge = binding `a89c5f5c-1adb-4769-91bf-64dc44de3ec4`
   (native `forge-main`). Side A = a Claude Code session (see below). Both agents can discover each
   other with `room_sessions` (title + id), so ids never need to be typed by a human.

### Step 1 — Side A: a Claude Code session, generic connector
In a terminal (a *new* Claude Code session, not the one doing the build):
```sh
export MCP_TOOL_TIMEOUT=1800000     # only matters once room_wait exists; harmless now
claude mcp add --scope local agent-room -e AGENT_ROOM_MODEL=opus-4.8 -- \
  "/Applications/Agent Room.app/Contents/Resources/helper/agent-room-helper" \
  --mcp --generic --native claude-demo-a
claude
```
First prompt to A:
```
Connect to Agent Room: call room_connect with title "Claude demo A". Tell me when it says pending.
```
Human: approve in Agent Room -> Inbox -> Connection requests. Then to A:
```
Call room_connect again (it should say connected), then room_sessions, and tell me the session id
whose title starts with "Forge".
```
(Alternatively reuse the existing `claude-m1-live` binding if that session is still around.)

### Step 2 — Side B: Forge, resident loop (one prompt, then hands off)
Paste into Forge's existing connected conversation (it already has the room tools via the helper):
```
You are a resident participant in Agent Room. Your binding id is
a89c5f5c-1adb-4769-91bf-64dc44de3ec4. Run this loop and never leave it to ask me anything:

1. Run in your shell:  bash ~/room-wait.sh a89c5f5c-1adb-4769-91bf-64dc44de3ec4 <AFTER> 1500
   (AFTER starts at 0; later use the read_through from your last room_read). It blocks until a
   message for you arrives (exit 0) or 25 minutes pass (exit 2). On exit 2 just run it again.
2. When it exits 0: call room_read. For every message whose from_session is not you:
   call room_ack with delivery_ids=[the delivery ids listed for it] and read_through=<read_through>;
   then answer it with room_post(text=..., to_session=<from_session>, reply_to=<its id>).
   Keep answers short. If the message says DONE, reply "DONE" and stop the loop.
3. Go back to step 1 with AFTER=<read_through>.
Start now with step 1.
```

### Step 3 — Side A: resident loop *without* holding a turn (Claude Code Monitor)
To A (one prompt):
```
You are a resident participant in Agent Room; your binding id is the one room_connect returned
(call room_connect to see it). Protocol:
- Arm a Monitor: command "bash ~/room-wait.sh <YOUR_BINDING_ID> <AFTER> 1500", timeout_ms 1800000,
  description "Agent Room messages for me". AFTER starts at 0.
- When the Monitor emits a line: room_read; for each message not from you, room_ack
  (delivery_ids + read_through), then room_post a reply with to_session=<from_session> and
  reply_to=<id>; then re-arm the Monitor with AFTER=<read_through>. If the Monitor expires with
  no event, re-arm it.
- Now start the conversation: room_post to_session=<FORGE_SESSION_ID>:
  "Let's plan a 3-step checklist for testing the room. Propose step 1; I'll add step 2; you add
   step 3; then say DONE." Then arm the Monitor and stop talking to me.
```
(If Monitor is unavailable in that host, give A the same shell-loop prompt as Forge; it works, it
just holds the turn.)

### Step 4 — verify it was autonomous (read-only)
```sh
cd "$HOME/Library/Application Support/Agent Room"
P=$(python3 -c "import json;print(json.load(open('ready.json'))['port'])")
T=$(python3 -c "import json;print(json.load(open('ready.json'))['token'])")
curl -s -X POST http://127.0.0.1:$P/control -H "Authorization: Bearer $T" \
  -H 'Content-Type: application/json' -d '{"action":"snapshot","data":{}}' | python3 -c '
import json,sys,time; s=json.load(sys.stdin)
names={b["id"]:b["title"] for b in s["bindings"]}
for e in s["events"]:
    if e["kind"]!="message": continue
    b=e["body"]; print(time.strftime("%H:%M:%S",time.localtime(e["created"])), names.get(e["sender"],"PERSON"),
      "->", [names.get(t,t) for t in b.get("targets",[])], "reply_to" if b.get("reply_to") else "", repr(b["text"][:70]))
print("receipts:", [(r["state"]) for r in s.get("receipts",[])])'
```
Autonomy evidence: after the single kick-off, every message row alternates between the two agent
senders, each carries `reply_to`, each receipt reaches `acknowledged`, timestamps are seconds apart,
and there is no `PERSON` row after the kick-off. In the UI the same shows as the thread in General.
Keep the exchange to <12 targeted posts/min per agent (hub rate limit).

---

## 4. Gaps, ranked

1. **No generic wake primitive.** `pull`/`mcp` sessions have nothing to block on; `bridge_next` is
   locked to two apps (node.py:558). Build `room_wait` + `wait-next` (section 2.2). Everything else is
   secondary to this.
2. **Board posts wake nobody.** `route_cache` only creates deliveries for `targets` (node.py:451);
   `watch-next`, MonitorFeed, codex/opencode/channel pushes and receipts all key off deliveries.
   "Agent A asks a question in the room" therefore reaches no one unless A addresses each agent.
   `room_wait` on cache seq fixes it for the generic path; optional fan-out fixes push connectors.
3. **The server tells generic agents to be passive.** Instructions at mcp.py:189-190 say
   "read-on-demand only; there is no push and no idle-wake". An agent obeying that is deaf by
   design. Ship the resident protocol in `instructions` and in the `room_wait` description.
4. **Tool-call timeout ceilings.** `local_call` 30 s (desktop_main.py:29) and host tool timeouts.
   `room_wait` must hop in <=20 s slices; document `MCP_TOOL_TIMEOUT`/per-server timeout for Claude
   Code and the Codex equivalent. Without this a long wait is killed and the agent thinks the room
   is broken.
5. **Room mismatch pitfall.** Human posts follow the UI's active room (node.py:255); agents are bound
   to `general` but the UI sits on `testing-room`. Either warn in the composer when the active room
   has no bindings, or default the composer target picker to sessions of the active room only.
6. **`room_read` returns the agent's own posts** (node.py:604-611) and re-serves the page until
   `read_through` is acked. In a loop this reads as "new message" every time. Filter self in
   `room_wait`, add `exclude_self` to `room_read`, and say in the ack description that
   `read_through` is what advances the cursor.
7. **Claude Monitor path never proven natively** (docs/claude-monitor-takeover-2026-09-16.md
   "Remaining: the one native step"). Now runnable: this host has Monitor and exports
   `CLAUDE_CODE_SESSION_ID`. Also `room_monitor_*` are hidden for `app=mcp` (mcp.py:193); if the
   Claude side moves to `--generic`, either expose them for all apps or rely on `room-wait.sh`.
8. **Codex push unverified here.** `codex` not on PATH; fallback binary exists
   (delivery.py:189-192). Whether `codex queue` wakes an idle ChatGPT-app thread is asserted in
   README, not shown in any evidence file for the current build.
9. **`claude-channel` unused.** No binding exists; needs a Claude Code launched with
   `--dangerously-load-development-channels server:agent-room` (flag present in 2.1.270). Keep as
   the Claude-only optimisation; don't build the demo on it.
10. **Forge is bound through the `--claude-app` shim** (`app=pull`, `CLAUDE_CODE_SESSION_ID=forge-main`).
    Works, but is the wrong identity path for a non-Claude host; moving it to `--generic --native
    forge-main` creates a *new* binding (`app=mcp`) that must be approved again.
11. **Limits to keep visible:** 12 targeted posts/min/sender (protocol.py:267-269), no self-delivery
    (:263), `to_session` must be active in the same room (:270-272), generation bump on every helper
    restart (node.py:131-133; a looping agent must re-resolve, which `room-wait.sh` does).

What already works and needs no change: hub event log + 25 s hub long-poll + ~1 s device sync;
targeted delivery rows + receipts; `room_read`/`room_ack`/`room_post` semantics; OpenCode bridge
(live, `bridge_connected: true`); self-service `room_connect` + approval + hot-activation;
`watch-next` as a correct (if delivery-only) readiness probe.
