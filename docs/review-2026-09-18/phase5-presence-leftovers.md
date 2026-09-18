# Phase 5 — stale agents and leftovers

Reviewed 2026-09-19 against 4a874df. Review only; no product edits, native build,
installation, external connector setup, or live-data access.

## Presence in plain words

There are four different states, not one “online agent” signal:

1. **Working/Idle/Blocked/Done is what the agent last said.** main.tsx:140–146 maps
   these strings. node.py:286–294 saves them in local binding JSON without a report
   timestamp or expiry. Missing state defaults to idle (node.py:211–218). Neither
   a successful tool read nor an exited process updates this state automatically.
2. **The participant list means registered, not alive.** main.tsx:571 filters the
   hub sessions by active. sync_once (node.py:379 onward) re-registers every local
   binding with the hub each cycle. protocol.py:210–235 reactivates an existing row.
   No desktop participant TTL is applied. A helper restart preserves self-report
   state while advancing connector generation (node.py:129–135).
3. **Bridge connected is recent transport activity.** snapshot (node.py:755–756)
   uses a 30-second monotonic bridge_seen window. bridge_next/heartbeat refresh it.
   delivery.py:70–83 independently expires claude-channel/opencode-bridge delivery
   sessions after 30 seconds, but does not remove local bindings or hub participants.
   pull/mcp have no equivalent heartbeat expiry. Codex queue is not proof a task lives.
4. **Monitor connected means socket transport, not agent availability.**
   monitor.py:24 limits watches to 1800 seconds; start gives an unused command 300
   seconds to connect, then a connected watch gets seconds+15 grace. Status uses
   socket/stopped/deadline state (:136 onward), not Working/Idle. On expiry/disconnect
   it clears its socket state; it never deletes the binding or sets agent presence.

room_wait (mcp.py:152–168) waits in <=20-second helper hops, total default 600,
clamped 5–1800 seconds. A timeout tells the client to call again. node.wait_next
(:626–661) validates identity/generation and checks unread room cache, but does not
update a last-seen time or presence. An instruction to “stay resident” is not a
running-process guarantee. No path here marks an agent gone when its caller exits.

**What should happen (proposal, not implemented):** preserve the connection and
history, but display stale/unknown availability separately from the last reported
work state. Record last contact/report, describe its age, and provide explicit
Disconnect. Do not auto-delete solely because a legitimate on-demand agent is idle.
Owner should choose expiry/label policy; a transport timeout must not mean task Done.

## Deterministic isolated probe

Script: phase5-probe.py; ran with python3. Temporary home created **under work/**,
MemoryVault, no real agent process and no credentials printed. Bound mcp, pull and
claude-channel synthetics, set all Working, aged wall/monotonic clock by one day,
ran expiry+sync, reopened Node, then tested online/offline removal. This is simulated
time, not a claim to have waited a day or killed a real external application.

Observed output (nonidentifying fields):

- simulated_elapsed_seconds=86400; activeCount=3.
- All bindings retained state=working; all bridge_connected=false.
- Hub active flags=[1,1,1]. Local delivery active: mcp=true, pull=true,
  claude-channel=false. This directly distinguishes delivery expiry from UI membership.
- After reopening the helper: restart_working_count=3.
- Offline remove: removed=true, local_binding_gone=true, hub_session_still_active=1
  **after subsequent successful sync**.
- Online remove: hub session active=0.

Proof classification: **read in code**, corroborated by an executed isolated Python
probe (not a browser click). Phase 3 already clicked Settings → Connections → Remove
and saw the binding disappear; this phase traces main.tsx:2309 to the same action.
No live/remote Mac state was inspected.

### Can the user clear stale agents?

**Online local binding: yes.** Settings → Connections → Remove → Remove connection
calls binding-remove with binding ID. node.py:296–324 deactivates at hub, deletes
binding/cursor/report/delivery rows locally, drops bridge lease. UI then filters the
inactive hub session out. Reconnecting same native identity reuses the hub ID.

**Offline: incomplete.** Hub removal is best-effort; the exception is swallowed before
local deletion. There is no durable pending-removal record or replay. After recovery,
the hub retains active=1 but Settings has no local binding row to remove again. This
is a confirmed stale-participant defect, distinct from the earlier wrong-key suspect
(which remains cleared). Proposed later fix: durable removal intent, idempotent hub
settlement, and explicit pending-disconnection UI. Do not silently delete hub history.

**Remote participants:** Settings lists local bindings, not arbitrary other-device
sessions. No per-remote-agent removal UI was found. Host device revocation is separate
and more disruptive; it should not be presented as ordinary stale-agent cleanup.

## Legacy files: used or dead?

Proof **read in code**. Import ledger in phase5-occurrences.md. Build scripts were
read, not executed; the installed/frozen bundle was not inspected.

| File/group | Current use | Evidence / safe conclusion |
|---|---|---|
| delivery.py | **Live shared dependency** | desktop/node.py:12 imports Delivery and dispatch_one. desktop_main.py imports Node; build-desktop.sh freezes desktop_main.py. Also used by legacy daemon/bridge. Do not delete it as an unused root file. |
| roomd.py | Legacy executable, not current desktop entrypoint | room_mcp.py:96 spawns it; install.py:178 writes launch configuration for it; test_delivery/test_transport run it. No current desktop import found. Still runnable, not globally dead. |
| room_mcp.py | Legacy MCP client, not desktop.mcp | install.py:19 selects it; legacy transport tests run it. It can autostart roomd.py and defaults to old port 8787/home. No desktop import/build entry found. |
| ui.html | Legacy daemon frontend | roomd.py:346 serves it. Vite/desktop uses apps/desktop/index.html and src/main.tsx, not ui.html. Archive/delete only with legacy-stack decision. |
| install.py | Legacy configuration installer | Configures room_mcp.py and roomd.py, includes OpenCode config writer. Not called by desktop build. Dangerous as current setup guidance; not run. |
| adapters/agent-room-desktop.ts and support opencode-client.mjs | Retired integration **still packaged** | tauri.conf.json bundle.resources maps ../../../adapters/ into adapters/. Plugin imports support module and OpenCode plugin SDK. Retirement is not complete in packaging. |
| scripts/build-desktop.sh | Current source build path | PyInstaller desktop_main.py with desktop.mcp/recovery hidden imports; pnpm build + Tauri. Not root daemon/web stack. |
| scripts/package-dmg.sh | Current packaging path | Packages verified built .app into DMG. No legacy daemon install command. Not executed. |

Old roomd.py uses a **15-minute presence TTL** (:32,226–238). That behavior must not
be attributed to the new desktop UI, whose self-reported states have no TTL.

## Retired OpenCode footprint

The complete tracked-text matching locations are in phase5-occurrences.md. Distinguish
executable support from historical evidence; do not delete safety rules/review history
just to make a grep return zero.

| Area | Remaining footprint | Meaning |
|---|---|---|
| UI | main.tsx app map, setup copy, connector option, directory field, plugin/setup details | User can still select retired connector; real reachable functionality, not only old docs. |
| Backend | node.py bind/request/bridge/tool paths; protocol.py app allowlist/native-ID validation; delivery.py registration/heartbeat expiry | Still accepted and serviced. Retirement requires coordinated allowlist/validation/transport cleanup, not UI-only hiding. |
| Adapter source | all three tracked adapters files | OpenCode-only plugin/readme/support; still bundled by generic resources mapping. |
| Dependency metadata | apps/desktop/package.json @opencode-ai/plugin and pnpm-lock.yaml records | Still declared/resolved dependency; no dependency install performed. |
| Tests | tests/opencode-adapter.test.mjs, test_desktop.py adapter/bridge fixtures | Preserve shared bridge/receipt coverage using supported connector before removing retired-specific tests. |
| Old installer | install.py install_opencode | Legacy configuration writer, not current app startup. |
| Current docs | README.md introduction/setup/workflow/tests; adapters/README.md | Still directs users to install retired support. |
| Historical docs | VERIFICATION.md, desktop-app-plan/research, handoffs/handover/results | Evidence and previous plans, not current authorization to reconnect. Mark obsolete guidance later rather than rewriting history in this review. |
| Toolchain path | Node/Playwright path under .local/share/opencode in review scripts/handover | Existing test-tool location, not a newly connected agent; moving toolchain is a separate portability task. |

No OpenCode process, plugin or configuration was installed, launched or changed.

## Synthetic agents and hardcoded identities

- **claude-m1-live:** only tracked documentation matches outside the review plan.
  HANDOVER.md:71 explicitly forbids re-adding the puppet, while fable-coordination.md:235
  suggests reusing it. This is contradictory setup guidance. No product-code match found.
- **Historical exact session IDs:** VERIFICATION.md and handover/coordination examples
  include UUIDs and ses_ identities; locations recorded without reproducing them. They
  are historical evidence, not defaults in current desktop code. Never copy them into
  a new host's shared MCP config.
- **forge-main/static identity example:** overnight-handover-2026-09-17.md:14 is a
  global-looking AGENT_ROOM_NATIVE example. Current generic identity resolver accepts
  environment/--native values; that is runtime configuration, not unique identity
  generation. Reusing a global fixed value conflates conversations.
- **Test/seed identities:** test_delivery.py canonical synthetic UUID; tests use agent-x;
  review seed uses seed-* and fixed fixture UUID; browser scripts use phase3-*.
  These are intentional reproducible fixtures and are not automatically loaded at
  application startup. They must stay isolated. The earlier Phase 2 probe left an
  inactive historical fixture in its test home; no inspection of live participants.
- **demo-a/demo-b:** historical RESULT/coordination documents describe puppets. No proof
  they remain in installed data; reviewing the live database is prohibited.
- **No hardcoded live UUID/native ses_ default found in current desktop Python/TSX.**
  This is a tracked-source scan conclusion, not an assurance about external MCP configs.

## Misleading docs to address later (list only)

| Document / location | Why misleading now | Disposition proposal |
|---|---|---|
| README.md:3,55–57,87,111 | Presents retired connector and test path as current supported setup | Update current support list/setup after retirement patch |
| adapters/README.md | Full retired installation guide and old/new room-tool coexistence advice | Archive with retired adapter or clearly mark unsupported |
| docs/handover-2026-09-18/HANDOVER.md:5,40–71 | Says nothing pushed/merged; old feature branch build steps; fixed identity rebind examples including OpenCode | Historical snapshot; current pickup/rules supersede it |
| docs/handover-2026-09-18/fable-coordination.md:235 vs HANDOVER.md:71 | Reuse test puppet vs never re-add | Explicit obsolete warning, not a runtime cleanup command |
| docs/overnight-handover-2026-09-17.md:14 | Fixed generic identity example may be copied across conversations | Document per-conversation identity requirement |
| docs/desktop-app-plan.md:76,96 | Retired connector is the next implementation milestone | Superseded plan; do not follow as current backlog |
| docs/desktop-app-research.md:22 | Says OpenCode has no adapter in base, while source bundles one | Dated research, not present architecture |
| VERIFICATION.md:333 onward | “No old ... source tree remains” describes external old installation, but legacy files remain in this repo; old work/agent-room-app path differs from current root | Clarify historical scope; do not erase validation history |
| docs/review-plan-2026-09-18.md | Old line counts, original branch/Phase-7-only merge schedule | Owner-approved sequencing in PICKUP is current; keep original as plan history |
| docs/review-2026-09-18/seed.sh header | Suggests system python3 helper despite keyring requirement; later environment doc corrects it | Correct example in future docs cleanup; use work/venv now |

## Findings / next phase

- **P5-01 High:** unbounded self-report displayed as current activity; no last-contact
  age or gone state. Code trace + simulated-time/restart probe.
- **P5-02 High:** offline Remove loses hub removal intent; active ghost remains after
  successful sync and local Settings row is gone. Code trace + isolated failure probe.
- **P5-03 Medium:** retired connector remains selectable, accepted, packaged and documented.
- **P5-04 Medium:** old runnable installer/stack plus contradictory identity instructions
  can reconnect the wrong system. Shared delivery.py prevents blanket legacy deletion.

No fixes performed. Tests: **187 passed in 26.14s**; desktop tsc --noEmit **exit 0**.
Next: Phase 6 only. Real process-death/remote-Mac UI timing not newly tested; simulated
clock and failure probes are reported honestly, not labelled clicked. Existing Phase 3
online-removal click evidence is reused with attribution.
