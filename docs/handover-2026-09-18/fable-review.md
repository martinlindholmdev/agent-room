# Fable review — `feat/overnight-build` (6 increments) — 2026-09-17

Repo: `/Users/irislindholm/Documents/Codex/2026-09-14/review-and-fix-the-agent-room/work/agent-room-app`
Range: `feat/persistent-agent-room-app..feat/overnight-build` (6 commits, 10 files, +1374/-341).
Read-only review. Nothing edited, built or installed. The installed app profile was not touched.

**pytest: 142 passed in 22.3s** (`python3 -m pytest tests/ -q`).

Beyond reading the diffs I ran three simulations in the scratchpad (repo untouched):
1. **Upgrade in place** — base-branch code wrote a realistic profile (3 bindings in `general`, messages, a delivery, a pending request), then the new code opened it. 22/23 checks pass; the one "fail" was my check being stricter than the design (`cursors` stays unset until the first new event; `cursor_for` falls back to the legacy key correctly). **No data loss, no re-fetch storm**: the first sync asks for events strictly after the legacy cursor, touches only `general`, fetches one snapshot. Old bindings load with `state=idle`, no `model`; the pre-upgrade pending request reads `room='general'` and approves fine.
2. **Rollback** — base-branch code re-opened the migrated profile: bindings/events fine, but every `request_create` fails (see H4).
3. **Edge probes** on the new code — results cited per finding below (`sim_probe_edges*.py` in the scratchpad).

## Verdict: NO-GO (for now)

Not for merging to main, and not for the installed-app cutover, until the Blocker and the four Highs are fixed. All five are small (one-line to ten-line fixes plus a runbook decision). The core backend work — migrations, per-room routing, cursors, PULL_LIKE — is sound and upgrade-safe. What is broken is the last mile: the shipped Tauri app cannot call any of the new actions, and two dialogs the new UI relies on do not exist in WKWebView.

**Fix first:** `apps/desktop/src-tauri/src/main.rs:15` — add `room-select`, `room-create`, `room-rename`, `binding-state`, `binding-remove` to `ALLOWED`, and add the parity test the plan already asked for. Without it, increments 3, 4 and 6 are invisible in the installed app.

---

## Blocker

**B1. The Rust IPC allowlist does not include any of the new control actions.**
`apps/desktop/src-tauri/src/main.rs:15` — `ALLOWED` still lists the 16 pre-branch actions. In the installed app every renderer call goes through `invoke("control")` (`apps/desktop/src/main.tsx:194`) and is rejected with "Unsupported action". So in the shipped bundle: clicking a room row, "New room", rename, "Remove", and the presence dot all fail. The increment-5 "verified live on localhost:1420" check passed only because the non-Tauri branch at `main.tsx:195` posts straight to the Python helper (`fetch("/control")`), bypassing the allowlist. Plan §4 explicitly called for "tie the two source-of-truth lists together with a test" — that test would have caught this. Fix: add the five actions; add a test that parses `ALLOWED` from `main.rs` and asserts it covers every action string passed to `act(`/`api(` in `main.tsx`.

## High

**H1. `binding-remove` race leaves an orphan delivery row that takes the whole node offline, permanently.**
`desktop/node.py:418-432` (`route_cache`) takes a `bindings` dict and then walks the entire cache outside any lock; `desktop/node.py:281-302` (`binding_remove`) deletes the binding and calls `delivery.forget` outside `self.lock`. If a `route_cache` pass (runs at least once per second) is mid-walk when Remove lands, it routes a delivery for the now-deleted session. Then `desktop/node.py:445-460` (`report()`) iterates that room, hits the orphan, calls `enqueue(..., sender=removed)` → `self.binding()` raises `session is not bound on this device` — on **every** cycle, forever. `send_loop` (node.py:463-474) catches it, sets `online=False, error='Connection unavailable'`, backs off; `dispatch_loop` sets "Delivery needs attention". Receipts stop for all bindings; nothing cleans the row; the user has no recovery path short of editing `delivery.sqlite3`. Reproduced in probe 2b (three consecutive cycles raise). Fix: in `report()` skip — and delete — delivery rows whose session has no binding; do the `bindings` membership check in `route_cache` under `self.lock`; hold `self.lock` across the DELETEs and `forget` in `binding_remove`.

**H2. The same native session can be bound into two rooms, which locks its MCP helper out.**
`desktop/node.py:216-232` (`bind`) matches `existing` by native+app only, then calls the hub with the *current* room; the hub's `UNIQUE(device,room,app,native)` happily creates a second session in the second room, and `save_binding` stores a second local binding. Trigger: the manual "Connect conversation" dialog (`main.tsx:2159`, `act("bind")`) used while a different room is active (the `request_create` path is guarded by `already-connected`). Consequence: `desktop/mcp.py:69-71` `resolve_binding` sees two matches → `SystemExit` → `run()` falls into "pending" mode; `try_activate` never matches exactly one; yet `room_connect` (mcp.py:82-84) answers "already connected". The agent is stuck with contradictory messages. Reproduced in probe 1 (2 local bindings, 2 hub sessions, SystemExit). Fix: `require(not existing or existing['room'] == room, 'session already connected in another room; remove it first')` in `bind()`.

**H3. "New room" and "Remove" depend on `window.prompt`/`window.confirm`, which Tauri 2's WKWebView does not implement.**
`apps/desktop/src/main.tsx:654` (`window.prompt("Name this room")`) and `main.tsx:972` (`window.confirm(...)`). Neither API is used anywhere in the pre-branch code. Reports for Tauri v2 on macOS say these calls silently return; one reports `confirm` returning `true` unconditionally. So "New room" is a no-op (null title → return), and "Remove" either no-ops or removes a live binding with **no confirmation**. Fix: use the app's own `Dialog` component (every other flow does) or `@tauri-apps/plugin-dialog`'s `ask()`. Sources: [docs-wiki issue #14 on window.confirm silently failing under Tauri](https://github.com/liyixin123/docs-wiki/issues/14), [wry release notes](https://v2.tauri.app/release/wry/).

**H4. Rollback after cutover breaks connection requests under the old helper.**
`desktop/node.py:100-105` adds `requests.model` and `requests.room` but leaves `PRAGMA user_version=1`, so the base-branch helper opens the migrated profile without complaint and then every `request_create` fails: `OperationalError: table requests has 8 columns but 6 values were supplied` (reproduced, rollback phase). The HTTP handler maps it to a 503, so an agent's `room_connect` just errors. The cutover already breaks the Keychain ACL, so a "reinstall the old bundle" retreat is a realistic path. Also the old code keeps reading the stale `cursor` key (new code only advances `cursors`), which causes a harmless re-fetch. Fix: bump `user_version` to 2 (the old code's "device schema newer than app" guard then refuses cleanly), and make the cutover runbook take a `backup` first and restore it on rollback.

## Medium

**M1. `session_remove` hard-deletes the hub session, unlike `revoke` (soft `active=0`), leaving ghosts.**
`desktop/protocol.py:158-170`. Reproduced consequences: (a) receipts targeting the removed session stay in hub `receipts` forever and the snapshot still lists them; the Inbox filter (`main.tsx:1265`) shows "Needs connection" for a session that no longer exists and `targetHealth` (`main.tsx:154`) says "Session is not active in this room" — no way to clear it (probe 8); (b) `work` objects owned by it become immutable — the human's cancel fails with `work owner must be an exact room session` (probe 4); (c) mid-dispatch removal: the prompt reaches Codex but the hub receipt stays `waiting` forever because `finish()` finds no row (probe 3). Fix: soft-deactivate (`active=0, generation+1`, matching `revoke`) and hide inactive sessions' receipts in the UI, or cascade receipts to `unavailable/'session removed'`.

**M2. Rooms cannot be shared with an already-paired device.**
No grant action exists in `hub_call` (`desktop/node.py:53-80`). A member-created room is invisible to the admin, and the admin cannot even `pair-create` into it (`room not granted`, probe 10); `pair_request` refuses existing device ids. For the single-Mac setup this is not a regression, but "multi-room" is effectively single-device and the UI gives no hint. Either document it as device-local for now or add an admin `room-grant` action.

**M3. `room_select` needs a live hub round-trip even to select the current room.**
`desktop/node.py:179-190`. Offline → `ConnectionError` (probe 5), so clicking any room while the hub is down shows an error; against a remote hub the call can block the UI up to 32s. The hub re-checks `access` on every request anyway, so validate against the cached `snapshot['rooms']` instead.

**M4. The generic connector's identity is per-config, not per-conversation.**
`desktop/mcp.py:61-62` takes `AGENT_ROOM_NATIVE`/`--native` — static values in an MCP config. Every conversation of that host shares one binding, one `offered` cursor and one ack state (probe 7: two "hosts" read identical pages), and a second conversation can never get its own binding (`already-connected`). This is exactly the anti-pattern the helper's own error text warns about (`mcp.py:71` "never set a shared session ID in MCP configuration"), and the handover recommends it for Forge. Security-wise it is **not** a new spoofing class: any local process holding the 0600 `ready.json` token can already call `tool` as any binding (ids, natives and generations are all in `snapshot`), and could already `request-decide` its own admission — same trust model as before. But it is a correctness trap. Fix: say so in the connect-dialog copy and docs; let hosts template a per-session value into `--native` where they can; see M5.

**M5. IdentityChip content is incoherent for exactly the read-on-demand types.**
`main.tsx:127-134` `appName('pull')` = "Read on demand", `appName('mcp')` = "MCP (any agent)", so the chip reads "● Read on demand · claude-opus-4-8" and "● MCP (any agent) · glm-5-3". The design's signature is *app · model*; the plan's central idea was self-reported app identity. The increment self-reports only `native` and `model`, not a display name, so Forge shows as "MCP (any agent)". Fix: add `AGENT_ROOM_APP`/`app_name` through request → binding; chip = name · model; delivery mode goes on the secondary line where it already is.

**M6. The smart views don't do what they say.**
`main.tsx:~615` the "Active" button's handler is `() => {}` — dead. "Needs you" shows `needsYou` = pending requests + blocked bindings (`node.py:649`) but navigates to the active room's Inbox, whose own heading count is requests + stuck receipts + failed outbox (`main.tsx:1258-1277`): two different numbers under the same name, and blocked bindings are listed nowhere. Being device-local, the views only ever reflect this Mac's own agents. Either build a real cross-room list or drop the pinned views until there is one.

**M7. Room context is missing where it matters.**
Connections rows (`main.tsx:925+`) and the approval card ("wants to join *this* room", `main.tsx:1218`) don't show the request's captured `room`, so approving from another room silently binds the agent elsewhere. Add a room label to both.

**M8. Test coverage misses the risky paths.**
142 tests, all green, but: no upgrade-path test with an old-shape profile (my simulation is the only one that exists); no Rust-allowlist parity test (would have caught B1); no cross-room isolation test at the tool level — `room_read`/`room_sessions` for a binding in room B against room-A traffic is untested (only posting is); nothing exercises `report()` after a remove or a remove mid-dispatch (H1, M1c); `stream_loop`'s multi-room polling is thread code with no test; the frontend has no tests and `tsc --noEmit` was never run. Suggested additions: parity test, old-profile upgrade test, isolation test, H1/H2 regression tests.

## Low

- **L1** `desktop/node.py:636-637` `snapshot()` JSON-parses every cached event twice per 1.8s UI poll (probe 6: ~2N `json.loads`). Filter in SQL or parse once.
- **L2** `PULL_LIKE` is defined three times (`delivery.py:17`, `protocol.py:21`, `main.tsx:126`) and `main.tsx` still hand-writes `["pull","mcp","codex-queue"]` five times (1270, 1290, 1303, 1356, 1654). `desktop_main.py:150` `--tool` choices omit `room_status`. Otherwise the generalization is complete — no stray `== 'pull'` comparisons remain in Python.
- **L3** `desktop/node.py:632-635` pre-sync fallback lists only the active room, so right after "New room" the sidebar briefly shows just that room (probe 9).
- **L4** Terminology drift: `activeRoom` duplicates `room` in the snapshot; `state` means four things (presence, request, outbox, receipt); `channel` (delivery) vs `room` (hub); UI copy mixes connection / binding / session / participant. Plan Phase 5 already lists this.
- **L5** Theme: the token system covers light mode fully — the only literal color outside the `:root` blocks is the modal scrim `rgba(0,0,0,0.5)` at `styles.css:1316`, commented as intentional. `prefers-reduced-motion` and `:focus-visible` are present. `--font-ui` puts `-apple-system` before Inter (design doc says Inter first) — no external fonts, fine.
- **L6** `main.tsx` is now 2,608 lines (+164); the planned refactor is untouched. By reading, I found no TypeScript blocker: `Circle`/`Play`/`Plus` are imported, `safe`/`act` signatures line up, the new optional fields are typed. Unverified by `tsc`.
- **L7** Hub `room_create` (`protocol.py:180-189`) has no rate limit and any member can create unbounded rooms; explicit `id` is accepted with only a length check. Same trust domain, negligible.
- **L8** Hub `sessions` still has no `model` column (self-flagged): a peer Mac's model is invisible.
- **L9** Mixed versions: old peer against new hub is fine (extra `rooms` key ignored); new peer against old hub gets an empty `rooms` list so `room_select` always rejects — acceptable degrade.

## Answers to the specific questions

1. **Correctness / data safety / upgrade.** Routing is right: agent content → its binding's room (`enqueue`, node.py:240), human content → active room, receipts → binding room, `room_sessions`/`room_context` → binding room. Request-time room capture works, including after switching away. Per-room cursors and the legacy `cursor` fallback are correct; the cache's global `seq` means no collisions. **The installed profile with 3 bindings in `general` upgrades in place without loss and without a re-fetch storm** (simulated). The caveats are H4 (rollback) and the transient one-sync window where `room_sessions` returns empty before the first `snapshots` write.
2. **Security.** No new spoofing class (M4 explains why). Local control API: every action, including `binding-remove` and `request-decide`, is reachable by any process with the 0600 token — pre-existing model, unchanged. `session_remove` is correctly scoped to actor device + room grant; `room_rename` is open to any granted device.
3. **Self-flagged edges.** Both are real. Mid-delivery remove is the mild one (M1c: stale `waiting` receipt); the serious variant is the orphan-row race (H1). Same-native-two-rooms is real and locks the helper out (H2).
4. **Code quality.** PULL_LIKE complete in Python; duplicated (L2). Dead: the "Active" button (M6). `activeRoom` duplicate (L4). `main.tsx` growth (L6).
5. **UX/design.** Tokens cover light mode (L5). IdentityChip is the right signature but reads wrong for pull/mcp (M5). Smart views are not meaningful yet (M6). Confusing: room-less Connections and approval cards (M7), offline room clicks erroring (M3).
6. **Tests.** 142 green; gaps in M8. `tsc` still needs to run once Node is available.

## Recommended order

1. B1 — allowlist + parity test.
2. H2 — one `require` in `bind()`.
3. H1 — skip/clean orphans in `report()`, lock the remove path.
4. H3 — replace `prompt`/`confirm` with the `Dialog` component.
5. H4 — decide: bump `user_version` to 2, and `backup` before cutover.
Then merge. Then M1 (soft-delete) and M6/M7 (UI honesty) before wider use. Cutover only after the parity test exists and a backup is taken.
