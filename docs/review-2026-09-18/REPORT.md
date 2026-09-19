# Agent Room review — final report

2026-09-19 · source baseline 3e13bf8 · phases 1–7 complete, with coverage limits below.
This is a source/dev-preview assessment, **not certification of the installed app**.
Owner authorized one critical fix batch between phases 3 and 4; it is merged in PR #2.
The installed app and live data were not updated. Owner controls deployment.

## The app as a user meets it

Agent Room has a usable core: a person can set up a Mac, create/switch rooms, approve
connections, post/reply, create planning objects, and choose a theme. Its main weakness
is trust in state: “Working”, a successful-looking save, a disappeared connection, or
an updated screen can mean something different from what the person assumes.

The first fixes stopped board posts flooding Inbox with invalid receipts, kept rejected
workflow saves visible in their forms, and stopped showing connected after a failed
helper poll. Those were tested against isolated helpers and browser interactions, not
rolled out to the owner's primary installed interface. Remaining failures are concrete;
more generic review is not a prerequisite to starting the next fix batch.

**The five worst open issues:**
1. Offline Remove loses the hub-removal request, leaving a ghost agent after reconnect.
2. A late old snapshot overwrites newer data; room/status displays can go backwards.
3. “Working” never ages out, even across a helper restart, and is not process liveness.
4. Saving an existing review resets verdict and findings even without changing its artifact.
5. Room changes and generic action completion lack operation scoping: stale recipients
   survive and an old action can close a newer dialog.

Retired OpenCode is still offered and bundled. Copy is inconsistent, setup exposes
implementation terminology, and keyboard/contrast defects make the interface harder to
use. A large rewrite is not the next step: fix lifecycle/state correctness in bounded
PRs, add browser/contract regressions, then extract components as those areas stabilize.

## B1 implementation follow-up — 2026-09-19

R01 is now fixed in source by B1; the original assessment below is retained as
historical evidence. Durable intent, restart/reconnect settlement, pending UI and
history-preservation regressions are documented in [B1](b1-durable-disconnect.md).
Checks: **198 passed in 25.60s**, desktop **tsc --noEmit exit 0**. No deployment or
live-data access. B2 and all other open findings remain untouched.

## B2 implementation follow-up — 2026-09-19

R02 and R07 are now **FIXED in source** by B2. Request/room generation guards reject stale successes and failures; cold helper failure stays unavailable until configuration is confirmed, with automatic recovery. See [B2](b2-ordered-snapshots.md): **11 controller tests + 6 synthetic Chrome tests passed**, **198 passed in 26.60s**, desktop **tsc --noEmit exit 0**. Original findings below are historical evidence for these two IDs. No deployment or live-data access. Stop before B3; R05/R06 and all other open findings remain untouched.

## B3 implementation follow-up — 2026-09-19

R05 and R06 are now **FIXED in source** by B3. Per-room retained drafts include
recipient/reply/ID; dialog-instance ownership prevents stale completion; operation IDs
track overlapping busy state. Room mutations cannot race pending actions. See
[B3](b3-scoped-actions-drafts.md): **6 state + 8 synthetic Chrome tests passed**, all
**17 B2 regressions passed**, **198 passed in 26.52s**, desktop **tsc --noEmit exit 0**.
Original R05/R06 findings below are historical evidence. Drafts are session-memory
only. No deployment/live-data access. Stop before B4; all other open findings untouched.

## Findings register

Open unless labelled **FIXED**. Duplicate phase findings are consolidated; detailed
occurrence-level copy/tooltips and control friction remain in strings.md/inventory.md,
linked by grouped rows below. No demonstrated whole-app Blocker is claimed.

Severity: High = wrong/misleading state or data; Medium = material friction; Low = polish.
Size: S = localized change, M = multi-layer bounded change, L = policy/migration or broad
work to split into smaller PRs; estimates include tests, not installation.

Paths: **UI** = apps/desktop/src/main.tsx; **CSS** = apps/desktop/src/styles.css;
**node** = desktop/node.py; **protocol** = desktop/protocol.py. Current line references
unless a historical phase ID is explicitly given. Proof labels: **both** = browser
interaction plus code trace; **read in code + probe** = isolated API/Python execution,
not a click. Synthetic browser responses are explicitly noted.

| ID | View | What the user sees | What should happen | Cause (file:line) | Severity | Size | Proof |
|---|---|---|---|---|---|---|---|
| R01 (P5-02) | Connections | Offline Remove disappears locally but agent remains at hub | Durable removal intent completes after reconnect | node:296–324 swallows hub exception then deletes binding | High | M | read in code + isolated failure/recovery probe |
| R02 (P6-01) | All views | Newer state replaced by older response | Only current request/room generation may apply | UI:431–447 overlapping refreshes | High | M | both; synthetic NEWER → OLDER response repro |
| R03 (P5-01/P3-09) | Presence | Quiet/nonexistent agent remains Working | Show last report and stale/unknown availability separately | node:286–294,738–758; UI:140–146,571 | High | M | both (32s browser observation); simulated-day/restart probe |
| R04 (F3) | Reviews | Save discards verdict/findings | Preserve unaffected review state; deliberate invalidation only | UI:2480–2488 forces pending/empty; protocol:320–330 | High | M | read in code |
| R05 (P6-02) | Dialogs/navigation | Old operation may close current dialog; busy ends too early | Scope completion/busy to operation and dialog | UI:481–498 global state, unconditional close | High | M | read in code; concurrency risk traced, not duplicate-write claim |
| R06 (F7/P3-04) | Composer | Draft/recipient survives room change, dropdown empty but target warning remains | Room-scoped drafts; explicit recipient reset/confirmation | UI:657–660,1706,1721–1734,2347–2350 | High | M | both for switch; cancellation/palette paths read in code |
| R07 (Phase 1) | Cold start failure | Helper unavailable looks like first-run setup | Separate unknown configuration from confirmed unconfigured | UI:99–123 empty.configured=false; :437–440,778–786 | High | S | both in Phase 1; current branch still retains empty configuration on first error |
| R08 (P6 backend audit) | Delivery/errors | Backend delivery failure may have no visible explanation | Render scoped operational health | node:580 sets snapshot.error; UI:751 uses local errors, not s.error | High | M | read in code |
| R09 (F2) | Workflow | Owner/reviewer change offered then rejected; missing completion evidence only discovered on save | Disable immutable assignment and validate state-specific required evidence | UI:2610–2649; protocol:314–324 | Medium | S | both for evidence; reassignment read in code; rejection presentation FIXED, invalid affordances remain |
| R10 (P6-06) | Workflow | Enqueue failure can leave form locked in check-status mode | Distinguish known rejected enqueue from unknown acceptance; allow safe correction | UI:2433–2453 pendingId before enqueue; API no timeout | Medium | M | read in code; accepted-pending synthetic case works |
| R11 (F6) | Palette/objects | Claim result opens an editor unable to save claim data | Read-only supported display or dedicated form | UI:275–284,2393–2399,2465–2494; protocol:340 onward | Medium | S | read in code; no claim browser fixture |
| R12 (F1/P3-05) | Empty room | Request a review opens work request | Open review form | UI:1485–1490; :2421 defaults work | Medium | S | both |
| R13 (F4/P3-06) | Inbox/sidebar | Different counters labelled as related needs; Active looks like navigation | Defined scopes and consistent selectors; clear static metric | UI:508–533,595–600,623–645,1282 | Medium | M | both; original 57-vs-no-badge count predates receipt fix, formulas still differ |
| R14 | Inbox | Other failed operations remain with no resolution path; object failure called message failure | Safe dismiss/retry policy and correct event-kind labels | UI:1326–1336; node cancel saved-only | Medium | M | both; do not automatically retry uncertain native sends |
| R15 | Rooms | No rename/remove UI, room settings opens app settings | Rename affordance; define archive/remove semantics first | UI:1811–1812; node:796 room-rename; no remove action | Medium | M/L | read in code; rename API exercised |
| R16 (P3-08/P6-05) | Conversation | Literal code fences; scrolling forced to bottom on event growth; no clear unread marker | Safe code rendering, near-bottom scroll and unread indicator | UI:475–480,1600–1602,1464 | Medium | M | both for code; scroll policy read in code |
| R17 (P5-03/F5/P3-11) | Setup/connections | Retired OpenCode still offered, accepted, packaged and documented | Remove reachable support/dependency while preserving necessary shared paths | UI:132,790,2180; node:228,328; protocol:211; tauri.conf.json resources; package.json:18 | Medium | M | both UI; build/import trace |
| R18 (P5-04) | Setup/docs | Old installer and fixed historical identities can point at wrong system | Archive legacy entrypoints; current safe identity guidance | install.py:19,178,204; room_mcp.py:96; HANDOVER:68–71 vs fable-coordination:235 | Medium | M | read in code; delivery.py explicitly remains live |
| R19 (P6-03) | API/errors | Generic inconsistent errors, no browser timeout/status check | Typed action/result/error contracts and bounded requests | UI:194–204,446; native main.rs:16–22; desktop_main.py:80–83 | Medium | M | read in code |
| R20 (P6-04) | All actions | Unexpected callback failure disappears; errors overwritten by concurrent actions | Surface unexpected failures; action-local error state | UI:501,577,1716,1774,2495; full catch ledger in Phase 6 | Medium | M | read in code; ordinary act failures already presented |
| R21 (P6-08) | Palette | Escape from result row does not close | Consistent dialog-level keyboard handling/focus restore | UI:290,304–315; result button :329 | Medium | S | both; synthetic Chrome Tab/Escape repro |
| R22 (P6-09/P3-12) | Dialogs | No accessible dialog name; initial focus often Close | Link title; focus useful field; restore opener | UI:380–395 | Medium | S | both for attributes; clicked focus observation |
| R23 (P6-10) | Themes | 8px helper text too faint | Normal-text contrast ≥4.5:1 and readable sizing | CSS:11–12,47–48,835–839 | Medium | S | both; measured 2.57 Light / 3.99 Dark |
| R24 (P6-11) | Presence/keyboard | Grayscale dots/tooltips carry state; palette cursor visual only | Accessible state text and keyboard selection semantics | UI:350–367,667–670,329–332,1832; CSS:188–205 | Medium | S | read in code |
| R25 (P3-13) | Narrow preview | Labels clipped in 64px sidebar | Real icon rail or readable collapsible nav | CSS:1495–1509 hides spans, not bare text | Medium | S | clicked screenshot 600px; native minWidth=760 limits installed exposure |
| R26 (Phase 4) | Copy/setup | agent/session/binding/room/board/object terms mixed; developer details in ordinary UI | Adopt glossary; separate Advanced setup | UI:946,2000,2196,2253–2288; strings.md occurrence ledger | Medium | M | read in code |
| R27 (P3-07/Phase 4) | Confirmation/help | Reconnect promises new identity; invitation always says General; composer implies every draft saved | Describe actual identity/scope/persistence | UI:2303,2107,1796; protocol:219–235; node pair-create current-room scope | Medium | S | both reconnect; other claims read in code |
| R28 | Empty states/onboarding | Missing list guidance; join submission lacks waiting-success state; all new objects called New request | Clear empty/action/success copy per context | UI:944–1013,2034–2081,2456; strings.md omissions | Medium | S | read in code |
| R29 | Architecture/tests | Large component and weak contracts let integration bugs escape | Characterization tests, typed API, incremental view extraction | UI:402–2404; package.json scripts; test_allowlist_parity.py:24–38 | Medium | L | read in code; 187 tests are not comprehensive UI assurance |
| R30 (P3-10) | Backup | Success appears in error banner | Separate success notice | UI:1034–1035,751–766 | Low | S | both |
| R31 | Copy/navigation | Start a plan drafts message; shortcut spacing/target misleading; hardcoded version/model; redundant/missing hover text | Match action label and platform; runtime version; useful tooltips | UI:1473–1482,1461,1025,2215; strings.md | Low | S | both planning action trace + Phase 3; remaining copy read in code |
| R32 (P6-07/storage) | Preferences/dev lifecycle | Theme may not persist silently; StrictMode would leave guard false | Explain storage limitation if needed; reset lifecycle ref correctly | UI:422,471,2428 | Low | S | read in code; StrictMode not enabled, not current production failure |
| FIXED-01 (P3-01) | Inbox | Board receipt flooding (historical) | No invalid hub reports; retain local delivery/ack | node:483–528; fix-feedback.md, PR #2 | High | M | both; 28 posts now zero failed receipt reports |
| FIXED-02 (P3-02) | Workflow | Rejected save closed dialog (historical) | Keep editable rejected form; close on confirmed result | UI:2329,2423–2453; node outbox-status; PR #2 | High | M | both; corrected evidence then saves; R09/R10 remain |
| FIXED-03 (P3-03) | Header | Failed helper poll retained connected status (historical) | Mark unavailable and recover | UI:437–440,721–729,770–773; PR #2 | High | S | both; R02 ordering and R07 cold-start remain distinct |

**Cleared suspect:** Settings Remove passes binding ID correctly. Online removal works;
R01 is lost offline intent, not the originally suspected wrong parameter key.

## Ordered fix batches — owner selects, one conversation and PR each

Each batch adds regression tests for its acceptance criteria; none authorizes installing
a bundle or modifying live data. Listed in recommended order, not one mega-PR.

| Batch | Scope / findings | Acceptance boundary | Owner decision |
|---|---|---|---|
| B1 Durable disconnect | R01 | Persist removal intent; reconnect/restart settles it; local pending state is honest; online/repeated removal safe | None for correctness; never delete message history |
| B2 Ordered snapshots | R02, R07 | Held old response cannot overwrite newer/other-room state; cold helper failure shows unavailable, not setup | None |
| B3 Scoped actions/drafts | R05, R06 | Old callback cannot close newer dialog; room switch cannot silently reuse another-room target; concurrent busy tracked | Choose per-room retained drafts vs explicit reset; recommend per-room drafts |
| B4 Safe workflow editing | R04, R09–R12 | Preserve verdict/findings when unchanged; immutable assignments clear; enqueue rejection editable; claim safe/read-only; correct review opener | Review invalidation policy; recommend invalidate only changed review artifact/version |
| B5 Honest presence | R03, R24 presence portion | Timestamp self-report/contact; stale label separate from work state; accessible text; restart/idle/on-demand tests | Choose stale threshold/wording; do not auto-delete idle connections |
| B6 Error lifecycle | R08, R10 timeout portion, R19, R20 | Typed bounded API, consistent envelopes, native parity, scoped visible errors without credentials | None; do not expose secrets in diagnostics |
| B7 Inbox consistency | R13, R14 | Defined badges/list counts; event-kind labels; safe dismiss/retry flow with fixtures | Define Needs you scope and failed-item dismissal; never auto-retry uncertain sends |
| B8 Keyboard/dialogs | R21, R22, R24 palette portion | Escape from any palette focus, named dialogs, correct initial/return focus and selection semantics | None |
| B9 Readability/layout | R23, R25 | Both-theme normal text contrast passes, readable small text, narrow nav verified | None; maintain monochrome design |
| B10 Retire connector | R17 | Remove option/runtime support/plugin bundle/dependency; migrate or clearly reject old bindings; supported-bridge tests retained | Existing retired-binding handling; retain history |
| B11 Safe docs/legacy boundary | R18 | Mark obsolete installer/identity examples; archive standalone legacy stack only after import/build checks; keep delivery.py or move safely | Archive legacy stack vs retain explicitly unsupported |
| B12 Copy and feedback | R26–R28, R30–R32 copy/storage | Approve glossary, accurate pairing/reconnect/persistence, correct new-form titles and success/empty text | Glossary approval; technical commands preserved in Advanced setup |
| B13 Room rename | R15 rename | Current backend exposed safely; active and inactive-room rename tests | None |
| B14 Room archival | R15 remove | Explicit archive/delete policy; protect messages, bindings and pending operations | Required: archive vs delete, default-room and active-agent rules |
| B15 Conversation reading | R16 | Safe code formatting, no scroll jump when reading history, unread indicator | Markdown feature/sanitization scope; no raw HTML execution |
| B16 Contract/test infrastructure | R29 contract slice | Portable assertion-based frontend harness/CI, runtime/API schema tests | None; avoid local tool-path dependency |
| B17+ Component extraction | R29 remainder, R32 lifecycle | Extract API/state first, then one view/dialog group per PR without redesign; characterization tests pass | Approve incremental investment; defer big rewrite |

**Recommended next authorization: B1, then B2.** They remove confirmed correctness
failures without waiting for naming/design policy. Presence and destructive room behavior
need owner choices; do not invent those policies during implementation.

## What was not verified, and why

- Real external agent reading/acknowledgement/review verdict, two physical Macs,
  revocation, sleep/wake, native login startup and installed webview: no live-app access,
  no second-device fixture; browser/helper evidence cannot substitute for these.
- Presence probe simulated a day and reopened an isolated Node; it did not wait a day
  or kill a real agent process. Offline removal used injected connection failure.
- Snapshot ordering and keyboard/contrast used real Chrome with synthetic API data,
  not a production load test. Full screen-reader/keyboard-only audit remains open.
- Not every workflow state/owner/decision/review combination, reconnect race, huge room,
  slow network, cold helper relaunch or long-running watch was exercised end-to-end.
- Historical root stack/build usage was traced through imports and scripts, not rebuilt
  or installed. Installed data may contain old agents; it was intentionally not inspected.
- Source inventory enumerates control templates and copy occurrences, not every runtime
  value, OS menu string or arbitrary exception. Phase 2 “works” verdicts were code traces,
  not clicks; those caveats remain part of this report.
- Phase 2 accidentally printed the **isolated** ready.json into the session transcript.
  It was not committed. No credentials belong in public artifacts. Probe cleanup retained
  inactive test history; it was not a byte-identical restoration of the fixture.

## Evidence and completed sequence

[Environment](phase1-environment.md) · [129-row inventory](inventory.md) ·
[Browser journeys](phase3-journeys.md) / [observations](phase3-results.md) ·
[First fixes](fix-feedback.md) · [Copy/glossary](strings.md) ·
[Presence/leftovers](phase5-presence-leftovers.md) / [occurrence ledger](phase5-occurrences.md) ·
[Architecture/catches/tests](phase6-architecture.md).

PRs #1 review 1–3, #2 first fixes, #3 copy, #4 stale agents, #5 architecture are merged.
Original single-review-branch/Phase-7-only merge schedule was superseded by the owner's
approved fix-first sequence. This final report is documentation only. After merging,
stop and ask the owner to select the next batch. **No further review phase is required.**

Final report checks: **187 passed in 26.83s** (python3 -m pytest tests -q); desktop **tsc --noEmit exit 0**, no output.
