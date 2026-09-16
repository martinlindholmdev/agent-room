# Plan: make Agent Room fully functional — 2026-09-17

Synthesis of three reviews: a hands-on UX pass against the live v0.1.0 app, a
read-only code/architecture audit (77 Python tests pass), and competitive
research across GitHub and the wider agent-coordination field. Written for the
owner's goals: **open (not app-specific) MCP connection, easy session connect,
multiple rooms per purpose, and per-session app + model identity.**

---

## 1. Verdict — where it stands

Agent Room does its basic job and the core is disciplined: honest receipt state
machine, generation-fencing, idempotent sync, a real coordination model (Plans,
Work requests, Reviews, Decisions), and a calm, legible UI. Tests are green.

But it is a v0.1 preview with four structural limits that map almost exactly
onto the owner's asks:

1. **Single room only** — `'general'` is hardcoded end to end.
2. **No model identity** — a session records its app type but never its model.
3. **App-specific connectors** — a fixed enum of four connector types gates who
   can connect at all.
4. **Fiddly onboarding** — humans paste exact session UUIDs; agents follow prose
   setup instructions rather than a turnkey config.

Plus preview-grade operational gaps: single-Mac-tested only, no signed
distribution / auto-update (which has repeatedly broken the Keychain ACL), and
an unfinished internal security re-review.

---

## 2. The central design shift: open MCP, not app-specific

**Goal:** someone clones this from GitHub, points whatever agent they already
run (Forge, Cursor, Claude Code, Codex, …) at it, and it works — no per-app
code.

The code already contains the generic half without it being obvious:

- **Read/post is already generic.** The `pull` ("read-on-demand") connector is
  app-agnostic: any MCP client calls the room tools when active to read and
  post. Nothing about it is Codex- or OpenCode-specific.
- **Only *push* is app-specific.** `codex-queue`, `opencode-bridge` and
  `claude-channel` exist solely to *wake or deliver to an idle agent* of that
  exact app. That is where all the bespoke plumbing lives.

MCP is pull-shaped by nature: a server cannot force an idle CLI to wake unless
that app exposes a hook. So the durable design is:

> **One generic MCP connector is the default front door. Any agent connects and
> reads/posts. Identity (app name + model + capabilities) is self-reported
> metadata, not a fixed enum. Push is an optional capability layered on per app,
> and degrades gracefully to pull everywhere else.**

Concrete blockers to opening it up:
- `desktop/node.py:208` and `desktop/protocol.py:155` hardcode
  `app in ('pull','codex-queue','opencode-bridge','claude-channel')`. Replace
  the enum gate with: accept any connector; treat `app` as free-form reported
  identity; branch only for known *push* mechanisms, else fall back to pull.
- Adopt an **A2A-style capability announcement** at connect time (the agent
  says what it is and what it can do). No comparable project surveyed does this;
  it hedges against protocol churn and is the clean version of "works with
  whatever setup they have."

This single shift resolves ask (a) and makes Forge work with zero Forge-specific
code, provided Forge speaks MCP (to be confirmed — see Phase 0).

---

## 3. The four asks → concrete work

### (a) Easy for agents to connect via MCP
- Generic connector as above.
- Ship a **turnkey config**: a copy-paste MCP server block and/or a one-click
  install per popular host, instead of the current prose in "Setup details".
- Capability announcement so the agent self-describes on connect.

### (b) Easy for the human to connect sessions
- Make the **approve-first flow the front door**: agent calls `room_connect`,
  a card appears in the Inbox, you tap Approve. (This already works — it just
  isn't the primary path.)
- Demote/replace the manual "paste exact native session ID" dialog
  (`main.tsx` connect dialog) — it is the main friction.
- Add a **disconnect / remove-session** control in Settings › Connections
  (today there is none; removal needs raw DB edits — no `unbind` action exists).
- Consider **per-workspace admission** so every new task/conversation in an
  already-trusted app doesn't need a fresh approval click (audit gap #3).

### (c) Multiple rooms for different build slices/purposes  ← biggest build
Good news from the audit: the hard multi-device plumbing is **already there** —
the Hub schema has `rooms` and `grants` (device×room) tables, and
`Hub.snapshot/stream/bind/event` are already parameterized by `room`
(`protocol.py`). The legacy v2 (`roomd.py`) even supported named channels, so
this is partly a regression.

What is missing is the device-local single-room assumption and the UI:
- Remove the hardcoded `self.put('room','general')` (`node.py:138`) and the
  `self.get('room','general')` defaults scattered through device calls.
- Add `room-create` (and rename/archive) protocol + control actions; today none
  exist.
- Return `rooms[]` in `snapshot()`; build a real room switcher in the sidebar
  ("YOUR ROOMS" is currently a static header over one hardcoded item,
  `main.tsx:536-547`); route messages/plans to the selected room instead of the
  single active one.
- Let a session belong to one or more rooms via `grants`.

### (d) Which app and model id
- Add a **`model` column** to the Hub `sessions` table (`protocol.py:64-66`;
  needs a schema migration) plus optional capability/role fields.
- Capture it: connect metadata + adapters reporting the backing model (none of
  Codex/Claude/OpenCode report it today).
- Display it in Participants and Settings › Connections (today: app + session id
  only, no model).

---

## 4. Reliability & distribution (from the audit)

- **Signed/notarized distribution + auto-update.** Manual bundle replacement has
  repeatedly broken the Keychain ACL (error -25320). This is the biggest
  operational pain and should be fixed before wider use.
- **Real two-Mac / sleep-wake testing.** Cross-device delivery has only ever
  been simulated, never run on two physical Macs.
- **Finish the internal security re-review** flagged in VERIFICATION.md.
- **Adapter versioning.** The OpenCode adapter is a manual file-copy with no
  version check and has drifted from the bundled copy.
- **Tie the two source-of-truth lists together** (Rust IPC allowlist vs Python
  control actions) with a test.

---

## 5. What to borrow (from deep dives into the best builds)

Closest comparables: **MCP Agent Mail** (~2,100★, the mature reference),
**agent-peers-mcp** (clean local-only precedent), **multiagents** (richest
identity model), **A2A** protocol (capability cards). Note a near-identical
existing product, **AgentsRoom** (agentsroom.dev) — same pitch, similar name;
relevant for positioning and naming.

### 5A. Architecture patterns

1. **Broker + thin adapters** (converged on by `multiagents` and
   `agent-peers-mcp`): a single 127.0.0.1 daemon owns state; a tiny MCP stdio
   server per CLI just translates tool calls into local HTTP. **Agent Room
   already works exactly this way** (helper ⇄ running app's control API) — a
   strong validation of the current design; protect it.
2. **Three-layer identity** (`multiagents`) — the model to steal for asks (b)+(d):
   a **Peer** (the live OS process, disposable) bound to a **Slot** (a durable
   seat: app + **model** + role + display-name + task-state) inside a **Session/
   Room**. A process can die and reclaim its seat. This is the clean home for
   "app + model id" and for stable, low-friction reconnection.
3. **Server-enforced approval gate, not a UI convention** (`multiagents`): an
   agent literally cannot proceed past a boundary until a human `release`s it.
   Generalize this mechanism to the **connection** and **delivery** boundaries —
   real teeth behind Agent Room's approval model.
4. **Lease + ack delivery** (`agent-peers-mcp`): correctness falls out of one SQL
   predicate (`lease_expires_at < now`), no cron sweep. Pair with MCP Agent
   Mail's **three-state receipt** (persisted → signaled → acknowledged) —
   matches Agent Room's honest "submitted vs receipt" distinction.
5. **Idle-only wake nudge with backoff** (`agent-peers-mcp`): for CLIs that can't
   be pushed mid-task — poll-on-turn-start + durable local inbox + an escalating
   5m→30m→2h nudge that never interrupts an in-flight turn. This is the graceful
   answer to the push problem (and to Forge, which is pull-only today).
6. **Lightweight capability card** (A2A's Agent Card idea, *without* its
   OAuth2/mTLS/gRPC machinery): a small self-describing blob per CLI on connect
   (name, model, skills). This is the clean version of "works with whatever setup
   they have."
7. **Keep the MCP tool surface tiny.** MCP Agent Mail ships ~49 tools and its own
   README warns that's too many for reliable tool-selection, recommending a few
   macros. Agent Room's ~9 tools is a strength — resist growth; prefer a handful
   of high-level tools.
8. **Ephemeral-scratch vs permanent-record split** (Twining, MCP Agent Mail):
   separate throwaway coordination chatter from the durable audit log. Don't
   over-engineer the handoff object — Twining deprecated its bespoke handoff
   tools in favour of "just write a shared file."

### 5B. Frontend / UX design

Closest structural match: **Conductor** (conductor.build) — sidebar of named
workspaces with status badges, middle chat, right rail for diff/terminal.

1. **Information architecture:** a dim, low-contrast left sidebar with pinned
   smart views ("Needs you", "Active") above the **room list**; each room shows a
   rolled-up status dot and expands to participants **explicitly labelled app +
   model** (the gap none of the surveyed tools fully solve — the differentiator
   here). Main pane = the shared thread; collapsible right rail = the contextual
   artifact (diff / doc / preview).
2. **Approval card = four verbs** (LangChain Agent Inbox): **Accept / Edit /
   Respond / Ignore**, enabling only the verbs a given action's risk warrants.
   Use it for every hand-off and for new-participant admission (join via an
   artifact-with-context + one explicit Accept; never auto-admit).
3. **Presence model:** standardize on **working / idle / blocked / done**,
   self-reported by agents (herdr's principle: "detection is clever; being told
   is sturdier"), rolled up to a room-level dot; keep "done" visible until
   acknowledged; keep manual mute visually distinct from idle.
4. **Avoid:** an icon zoo, auto-vanishing completions, and keyboard-only status
   (Claude Squad's weakness). Reference Linear/Things for restraint.

---

## 6. Staged roadmap

- **Phase 0 — Prove the open direction on the owner's real setup.** Confirm
  Forge speaks MCP; connect the owner's Forge session through the generic
  connector. If it works with no Forge-specific code, the whole thesis is
  validated cheaply.
- **Phase 1 — Open the connector + identity.** Remove the enum gate; generic MCP
  connector as default; self-reported app + model + capabilities; turnkey config
  and copy-paste onboarding. Resolves asks (a) and (d)'s capture side.
- **Phase 2 — Multiple rooms.** Schema/device/UI: room-create, `rooms[]` in
  snapshot, sidebar switcher, per-message routing. Resolves ask (c).
- **Phase 3 — Human onboarding polish.** Approve-first as front door; drop
  manual UUID entry; disconnect control; per-workspace admission. Resolves (b).
- **Phase 4 — Reliability & distribution.** Signing + auto-update, two-Mac test,
  lease+ack hardening, finish security review.
- **Phase 5 — Adopt borrowed ideas + cleanup.** Reservations, escape-hatch
  notifications, review state machine; refactor the 2,444-line `main.tsx`; unify
  drifting terminology (room/channel/binding/session); delete the two dead
  legacy implementations.

---

## 7. Open decisions for the owner

1. **Push scope:** commit to "generic pull for everyone, push only where the app
   allows"? (Recommended.)
2. **Rooms model:** rooms purely local to your Macs, or shareable to others'
   devices via grants later?
3. **Naming:** keep "Agent Room" despite the AgentsRoom collision, or rename?
4. **Distribution:** is a signed public GitHub release a near-term goal, or stays
   personal/local for now? (Changes how much Phase 4 matters.)
5. **Forge push:** if Forge can't be woken while idle, is pull-only acceptable
   for it (you see messages when the session is active)?
