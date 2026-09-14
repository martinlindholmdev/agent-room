# Agent Room desktop app — build brief

Prepared 2026-09-14. User authorized research, improvements, and a new task to implement. This is a proposed product and implementation plan, not a claim of completed functionality. Research and limitations are in desktop-app-research.md. Live connection details are supplied separately outside Git.

## Product outcome

Install Agent Room on each Mac. Join a room once, connect the agents you choose, and let their existing conversations exchange messages, plans and reviews. Closing the room window should not lose conversations or interrupt delivery. Sleeping devices catch up when they return. The person sees what needs attention and can intervene in any conversation.

Preserve native agent sessions and their existing permissions. The app coordinates work; model execution stays in Codex, Claude Code, OpenCode and future adapters. Basic routing, persistence and search require no additional model subscription or inference call. Persistent means durable coordination, not endlessly running models.

## Decisions

| Area | Build direction | Reason / limit |
|---|---|---|
| Desktop | Tauri 2, TypeScript, Vite and a small React frontend | Native downloadable Mac app with a reusable UI; validate toolchain early. |
| Existing core | Retain tested Python room/delivery behavior; package a standalone helper | Preserve receipts and compatibility. Do not rewrite the backend just for stylistic consistency. |
| Persistence | Transactional hub event store and per-device durable outbox/cache | Survives disconnected devices and process crashes. Migrate existing JSONL/state deliberately. |
| Network | One authoritative hub, initially a chosen Mac, reached privately over Tailscale HTTPS | Simple ordering and operation; a sleeping hub delays cross-device delivery. Optional always-on hosted hub later. |
| Agent access | Each Mac's connector talks only to its own registered sessions | Native server passwords and local APIs stay on that Mac. |
| New sessions | One-time workspace opt-in plus supported lifecycle integration | Automatically offer/join the selected room where the host supports it; explicitly show unsupported hosts. |
| User experience | Monochrome room conversation with a compact context panel | Planning/review happens beside discussion, without a separate elaborate project manager. |

Tauri sidecar packaging and login startup support the design, but neither alone guarantees service survival. Implement and test a supervised helper with explicit start, pause and stop behavior. No system Python or Node dependency for an installed end user. Builder may revise these choices with concrete evidence, keeping the product outcome.

## Everyday flows

**First Mac:** Open app → create room → choose device name → connect a supported agent → confirm the exact conversation → exchange a test message and actual agent receipt. Offer background/login behavior with an understandable setting. Do not label a connection working just because an API returned success.

**Another Mac:** Install the same app → join using an expiring pairing link/code → approve the new device on a trusted device → select local agents/workspaces. The connector uses an outbound connection to the hub. Room credentials and native agent credentials are separate. Pairing should make topology a secondary detail, while explaining which device must stay online.

**Existing session:** Bind its native session ID and directory, preserving conversation. Detect capabilities first. If a restart/resume is required, show the exact command for that same session and why; never silently launch a replacement.

**New session:** Supported plugin/lifecycle hooks discover it in an opted-in workspace. Its distinct identity joins with selected role and room. Supply a concise catch-up packet: current objective, accepted decisions, unresolved requests, ownership and linked source messages. Do not replay the entire transcript or acknowledge unseen history. A resumed session retains its own cursor and pending deliveries.

**Ask for review:** Select reviewer → attach immutable commit/diff/artifact and test evidence → reviewer acknowledges then responds with findings/verdict → author fixes → changed artifacts require a new review. The room retains the discussion and evidence.

**Pause and reconnect:** Show which messages are saved locally, waiting for hub/device, submitted to a host, and acknowledged. Reconnect from durable cursors. Reassignment of work from a closed session is explicit and preserves original routing history.

## Interface

Use black, white and neutral greys; generous but efficient spacing, restrained typography, thin separators, native-feeling controls. Use OpenWork/OpenCode as aesthetic references, creating an original interface. No decorative gradients, oversized dashboard cards or colour-only status signals. Support light/dark appearance, keyboard navigation, focus visibility, accessible contrast and reduced motion.

Left sidebar: Inbox, rooms and search. Main pane: readable conversation, threads, targeted composer and quiet receipts. Collapsible right pane: participants, current plan, work requests and decisions. Device setup and diagnostic IDs belong in settings/detail views. Participants normally show agent app, device and task title, never require copying UUIDs.

Inbox groups “Needs you”, “Waiting on agents”, and completed work. Notify on a direct question, blocker, requested review or completion; routine acknowledgements remain quiet. Add Cmd-K navigation and source-linked search. Offer summaries on demand or at meaningful milestones, with provenance and no fabricated decisions.

## Collaboration features

1. **Two-way threads:** request ID, reply-to, exact sender/recipient and correlation to receipts. Normal conversation remains first-class. Agents can ask follow-ups and disagree.
2. **Work requests:** owner, role, scope, due/expiry where useful, acceptance and completion evidence. States: proposed, accepted, working, blocked, ready for review, resolved/cancelled. Transport acknowledgement is separate from task acceptance or completion.
3. **Shared plans and decisions:** versioned plan steps and attributable decisions, with proposal/accepted/superseded state. Show who accepted a decision. An agent decision never silently expands the user's authorization.
4. **Review packets:** immutable artifact revision, base revision, author, reviewer, checks and findings. Invalidate stale approvals after changes. A self-review is visibly labelled. Reviews do not automatically merge, publish or deploy.
5. **Ownership:** advisory claims for repository/worktree/branch/path scope with leases, explicit release and visible conflicts. A claim is coordination metadata, not a filesystem lock or authority to overwrite changes.
6. **Role discovery:** show available planners/reviewers/implementers, capabilities and current load. Resolve a role to an explicit registered session and preserve that choice. Ambiguous identity must not silently route to another conversation.
7. **Context handoff:** durable packet with objective, decisions, pending questions and artifact references. Bind local checkout paths separately on each Mac; never assume equal paths or transfer private files automatically.
8. **Conversation controls:** pause room/agent, cancel unsent work, bounded rounds and expiry. Receipts are state events, not new prompts. Prevent reflection loops and repeated model invocations. Do not pretend cancellation recalls prompts already accepted by a host.

Implement the useful core of these features incrementally; avoid a plugin marketplace, general workflow engine, autonomous model router or rich document editor in the first release.

## Delivery and identity contract

Identity combines room, device, app installation, native session ID and connection generation. Display names are labels. Reconnect can renew the same verified binding; a new native session is a new identity. Use generation fencing to prevent stale connectors dispatching after reconnection.

Each event has a stable ID, room sequence, authenticated sender, exact target, thread/request/reply references, timestamps and protocol version. The sender persists locally before showing “Saved”; the hub persists before acknowledging; a destination deduplicates before native dispatch. Store per-device stream cursors transactionally. Bound queues, payload sizes and reconnect backoff, with visible failures.

User-visible progression: Saved locally → Waiting for hub/device → Submitted to agent app → Agent acknowledged. Work acceptance, response and completion are separate. Keep existing pending/submitted/acknowledged/unavailable/uncertain receipts compatible while extending them.

At-least-once network transport with durable deduplication does not imply exactly-once model execution. If a native API lacks verified idempotency and a send result is ambiguous, record uncertain and reconcile; do not blindly retry. Preserve the existing bounded pre-launch retry behavior. Human messages get priority among unsent messages; already queued host work may not be interruptible.

Use an authenticated event stream with replay cursor for delivery and return receipts. No agent room polling loop or constant model wakeups. Transport keepalives/reconnects are fine. SDK plugins should return answers through the room/MCP path; correlate replies to requests rather than scraping whole transcripts.

## Adapter work

**Codex:** retain proven exact-task local queue adapter. Idle wake and busy next-turn delivery were verified; mid-turn interruption was not. Remote Codex delivery executes through the destination Mac connector. Do not assume local control sockets or private host APIs are universally available.

**OpenCode — first missing adapter:** connect to the existing desktop server with the exact directory and session. Use prompt_async and supported event/lifecycle interfaces; verify installed schema and busy-session behavior. HTTP 204 is submission only. Use explicit room acknowledgement and a reply to prove two-way receipt. The user's Astra investigation found renderer IPC discovery; treat it as a version-specific integration candidate requiring a secure, supported bridge, not an HTTP endpoint or automatic external access. A plugin with supported client context may be a better integration. Do not scan memory/databases for secrets or log them.

**Claude Code:** preserve experimental channel adapter and exact connection lease. Existing Claude session owner is testing resume/channel delivery; coordinate rather than editing their config concurrently. Custom channel allowlist and organization requirements may prevent zero-click onboarding. A closed session cannot be awakened by this adapter. Keep an honest unsupported/needs-setup state and precise same-session resume instructions when verified.

Each adapter reports capabilities separately: discovery, current session binding, idle wake, busy delivery, resume, receipt, cancellation and native idempotency. “Connected” must not imply all are supported.

## Trust, data and operation

Pair devices using short-lived single-use proof over authenticated TLS plus trusted-device approval. Issue revocable device credentials scoped to rooms and actions. Authenticate sender identity instead of trusting body fields; only local connectors may bind their local sessions. Do not remotely accept arbitrary executable commands, local paths to open, or native server URLs from a room message.

Use Keychain/native credential storage for long-lived device credentials; keep transient OpenCode secrets in local process memory where possible. Never place them in room events, Git, URLs, diagnostic output or assistant-visible tool output. Tailscale membership complements app-level authorization. Expose only the scoped hub protocol; prevent legacy shared-token routes from bypassing new authorization.

Keep personal runtime data outside the repository. Add consistent backup/export and tested restore. Render message content safely and restrict desktop IPC capabilities. Diagnostics contain event IDs, versions and state transitions, excluding bodies and credentials by default. Do not sync a live SQLite database through a shared folder.

Migration must preserve original journals, unread cursors, pinned routes and pending/uncertain sends. Back up consistently, stop competing writers, migrate transactionally, verify schema version and rollback behavior. Never restore a stale backup over messages received since it was created. Run app development on isolated ports/data first. Preserve the live service and Iris runtime while other sessions use them.

## Implementation sequence and exit checks

| Milestone | Deliverable | Evidence required |
|---|---|---|
| 1. Real adapter and runnable shell | OpenCode adapter contract/implementation plus basic desktop room connected to isolated real backend | Exact existing session gets synthetic request and sends receipt/reply, or a precise remaining connection blocker; runnable app still progresses. Existing 21 tests remain green. |
| 2. Durable single-device app | Background helper, conversation, recipients, receipts, reconnect and actionable errors | Close window, restart helper and reconnect without losing/duplicating messages; no secret leakage; native app build and visible interaction checks. |
| 3. Multi-device protocol | Scoped pairing, one hub, durable device queues, event stream, generation fencing | Automated failure/replay/auth tests; then real Mac A → agent on B → reply to A, plus sleep/wake. A simulated pair alone is not proof of two real Macs. |
| 4. Planning and review | Work requests, plan/decision log, review packets and advisory ownership | Two agents plan/review a synthetic artifact; revisions invalidate review, replies route correctly, no endless acknowledgement loop. |
| 5. Distribution and onboarding | Installable bundle, clean-machine setup instructions, updater wiring, versioned migration | Bundle runs without developer runtimes. Signed/notarized distribution only when signing resources exist; safe update/recovery verified. |

Implement across milestones while recording completed, tested, and externally blocked items separately. Ship a reviewable working local app early. Do not stop at a static mockup or claim all-vendor/two-Mac support from a fake client test. If credentials, a second device, signing or host restrictions block a live check, finish independent implementation and leave a specific reproducible check.

Useful initial engineering targets (unmeasured): app usable within 3 seconds cold; local persisted message feedback within 200 ms; online cross-device handoff within 2 seconds excluding model work/host busy time; low idle CPU and bounded memory/queues. Measure on the actual Macs before claiming targets met.

## Work location and completion report

Build in the isolated feat/persistent-agent-room-app worktree supplied by the planning task, based on 6137aad. Suggested additions: apps/desktop, adapters, protocol schemas and focused tests; retain existing core entry points until migrations justify changing them. There is no Git remote, so make local commits and do not invent a push destination.

Keep README/VERIFICATION current with precise host/version capabilities and real evidence. The completion report should link the runnable artifact, summarize how to start/connect it, show what was tested, and state remaining host/device/signing limits. No Iris source, runtime, calendar/mail integration or unrelated application configuration changes.
