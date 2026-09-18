# Phase 6 — architecture, reliability and accessibility

Baseline 55f9ada, reviewed 2026-09-19. No product changes. References main.tsx unless
qualified. Prior fixes remain in place; this review does not claim they solve every
race. Evidence is **read in code**, or **both** where the synthetic browser probe
reproduces it. phase6-browser.cjs uses real Chrome DOM with synthetic /control
responses; it never contacts a helper or reads credentials/live data.

## 1. Split by responsibility, not a rewrite

main.tsx is now **2,662 lines**, not the plan's original 2,624. App spans :402–2404;
Palette, Dialog, IdentityChip and Workflow already exist as components in that file.
Moving files alone will not fix state ownership or API contracts.

| Suggested module | Responsibility / user benefit | Indicative effort including tests |
|---|---|---|
| api/control.ts + types.ts | Typed action request/response union, safe error envelope, fetch timeout/cancellation, native wrapper; prevents wrong keys and error-field collisions | 0.5–1 day |
| state/useRoomSnapshot.ts | Single-flight polling, generation/room guard, refresh result, connection health; prevents stale room/status reversal | 1–2 days |
| views/RoomView + MessageList + Composer | Room-scoped drafts/recipient/reply and scroll policy; stops cross-room draft targeting and forced scroll | 1–2 days |
| views/InboxView, ObjectsView, SettingsView, SetupView | Explicit props and view selectors; consistent counts and testable empty states | 1–2 days |
| dialogs/WorkflowDialog, ConnectionDialogs, PairingDialogs | Operation lifecycle and validation owned by form; prevents a completed old action closing a new dialog | 1–2 days |
| components/Dialog, Palette, IdentityChip, Sidebar | Focus/accessibility and shared labels; consistent keyboard behavior | 0.5–1 day |

Rough total **5–10 focused engineering days**, not a delivery promise. Prefer several
small PRs: first add characterization tests and central API types, then fix state
races, then extract unchanged views. Do not bundle visual redesign with extraction.
No need for a global state library yet: room identity, operation IDs and polling
ownership are the missing abstractions, not a particular framework.

## 2. State and async findings

| ID | User impact | Cause / evidence | Proof |
|---|---|---|---|
| P6-01 High | Old data can replace newer room/state data | :431–447 interval launches overlapping refreshes; no request sequence, AbortController or selected-room generation. Probe held first snapshot, returned NEWER second, then released first: device label changed NEWER → OLDER. | both |
| P6-02 High | Switching room or opening a different dialog while an action finishes can apply stale effects | :481–498 act refreshes then unconditionally closes current dialog; single global busy can be cleared by first of concurrent actions. Many nav/actions are not disabled; callbacks capture old room/target. | read in code; concurrency consequence traced, not a duplicate-write claim |
| P6-03 Medium | API failure details can disappear or be inconsistent between preview/native | :194–204 fetch parses JSON without HTTP-status check/timeout; error truthiness assumes envelope. Native wrapper times out at 35s and uses different messages. :446 runtime_info promise has no rejection handler. | read in code |
| P6-04 Medium | Unexpected callback errors silently vanish | safe/formSubmit and handler catches listed below suppress all rejections, not just already-presented act errors. | read in code |
| P6-05 Medium | New messages pull user away from old messages | :475–480 scrolls bottom on any growth in events count without checking near-bottom or room identity; receipts/objects also grow event count. | read in code |
| P6-06 Medium | Save form can remain locked after enqueue failure with no saved operation | Workflow sets pendingId before onSave (:2433–2436); any failure leaves ID and disabled fields. Same-payload retry handles lost response safely but permanent enqueue rejection has no edit/reset distinction. Missing timeout on status fetch can also defeat the nominal 12-second loop. | read in code |
| P6-07 Low | StrictMode/dev remount would leave mounted guard false | :2428 cleanup flips ref false, setup never restores true. Current root is NOT StrictMode, so not a current production repro. | read in code |

Send has no synchronous in-flight guard (:553); busy is React state, not a mutex.
Rapid handlers can submit the same draft ID, but backend enqueue rejects differing
content and deduplicates identical ID/payload (node.py:248–266). Do not call this
proven duplicate delivery. Form room-create has no comparable UI request ID; disabling
a button after render is not a general exactly-once guarantee.

**Recent fix status:** refresh catch now sets online=false, and workflow polls persisted
outbox-status. Synthetic pending result held form open, fields disabled, with a check
status button after ~12s. Correct behavior for an accepted pending save; P6-01/P6-06
are separate remaining cases. Closing Workflow prevents later successful result from
closing another dialog via mounted guard, but generic act callers lack that guard.

## 3. Every frontend catch, including deliberately handled cases

| Location | Behavior | Finding / recommendation |
|---|---|---|
| :422 | localStorage read → system theme | Swallowed storage failure; low risk, deliberate graceful fallback. Test blocked storage. |
| :437 | refresh error → connectionError/offline | Presented, not swallowed; retain stale content but label it stale. Sequence responses. |
| :471 | localStorage write ignored | Theme works now but will not persist, no user explanation. Low-priority persistence notice if blocked. |
| :493 | act sets error then rethrows | Presented API failure. Global banner can be behind modal; prefer form-local feedback. |
| :501 | safe(fn).catch(empty) | API error normally already presented by act; exceptions after act or in callback vanish. Unexpected-error boundary/logging needed. |
| :577 | formSubmit callback.catch(empty) | Same issue; covers create/join/new-room/connect forms. Do not blanket-call these errors visible. |
| :923 | set_login_start catch setsError | Presented native failure; no silent catch. |
| :1716 | composer submit send.catch(empty) | act normally presents API error; later send/focus errors swallowed. |
| :1774 | Enter send.catch(empty) | Same as submit; duplicate swallowing path. |
| :2450 | Workflow submit catch sets saveError | Presented inline; pendingId distinction between known rejection/unknown acceptance still needed. |
| :2495 | submit(data).catch(empty) | Normally redundant because submit handles errors; unexpected rejection swallowed. |

No other catch sites found in main.tsx at this baseline. :446 runtime_info is an
**uncaught** rejection, not a swallowed catch. UI error state can also be overwritten
by another operation's setError(empty) even when each operation technically reports.

### Backend suppressed-error context (not an exhaustive repository exception audit)

- node.py:305: hub removal failure swallowed before deleting local binding; confirmed
  P5-02 data/state mismatch, needs durable pending removal rather than logging alone.
- node.py:397/400: validation saved to outbox failed; transient reset to saved and
  rethrown. Appropriate distinction; UI must render action kind and rejection cause.
- node.py:542: send loop collapses all failures to offline/backoff; diagnostics lost.
- node.py:567: stream failure only waits 3 seconds; no user diagnostic. Polling may
  still work, so do not falsely mark whole app dead; expose degraded stream separately.
- node.py:580: dispatch failure sets snapshot.error, but renderer never renders s.error;
  global error/connectionError are different local state. Delivery failure can be hidden.
- mcp.py:140 activator retries silently; :187 channel retries silently; :266 returns
  generic tool failure. Distinguish expected reconnect from permanent configuration errors.
- monitor.py:182 closes feed on errors without cause; :189/199/206 ignore close/unlink
  errors as cleanup. Expected teardown need not alert user, but retain bounded diagnostics.
- Native Rust window show/focus, child supervision and cleanup use ignored Result/.ok();
  failures are not automatically UI-visible. Native runtime testing remains outstanding.

## 4. UI ↔ control API agreement

| Contract | Verified mapping / gap | Needed protection |
|---|---|---|
| send | UI id,text,targets,reply_to → node control/enqueue; target must be hub session ID, not native | Type request; room-bound draft ID and recipient reset; regression for room switch |
| bind | app,title,native,directory,model; backend chooses selected room unless supplied | Explicit room in operation context; precise connector validation |
| binding-remove | binding:editing.id → resolver accepts binding ID | Wrong-key suspect remains cleared; durable offline removal is different bug |
| request-decide | native+app+approve → request row; stored request room preserved | Test approve after room switch (backend already captures room) |
| object | id,type,version,data,event_id → enqueue; kind-specific protocol validation is later | Confirm outbox result (implemented); distinguish validation retry vs pending unknown outcome |
| outbox-status | id → id,state,reason (not error) | Keep reason separate from API error-envelope semantics; native allowlist now includes action |
| pause | paused boolean → durable setting | Show dispatch-only semantics, not message recall |
| room-select/create | room / title → global active room | Avoid concurrent global room switches and stale responses |
| pairing/revoke | id / device passed through node with current room | Pair invitation copy must use actual scoped room |
| errors | preview HTTP errors often generic; native string errors; outbox detailed cause | Discriminated success/error schema, status check, typed errors and action-local display |
| snapshot | TypeScript s accepts spread empty+next, no runtime validation | Validate arrays/key fields; do not equate TS interface with validated network data |

Python allowlist parity test catches literal act/api names missing from Rust ALLOWED;
it caught the initial outbox-status omission during the fix batch. It does **not**
check request fields, response envelopes, dynamic names or behavioral semantics.
Generic Record<string,unknown>, Promise<any>, editing.data:any and runtime:any bypass
compile-time end-to-end contract guarantees.

## 5. Accessibility basics

| ID | Observation | Evidence / recommendation |
|---|---|---|
| P6-08 Medium | Palette Escape only works while search input handles it | Both: open palette → Tab to result → Escape left palette open (count=1). Native dialog uses open, not showModal; onCancel does not provide modal Escape behavior. Handle keys at dialog and restore focus. |
| P6-09 Medium | Dialog has heading but no accessible name linkage | Both: DOM aria-label=null and aria-labelledby=null. Dialog h2 lacks linked ID. Add labelledby; test accessible role/name. Palette input name is not dialog name. |
| P6-10 Medium | Small helper text fails normal-text contrast in both themes | Both: computed .composer-help 8px; Light rgb(162,162,155) on white = 2.57:1; Dark rgb(119,119,115) on rgb(23,23,23) = 3.99:1. Below 4.5:1 normal text. Measurements from rendered CSS, not a full WCAG audit. |
| P6-11 Medium | Presence communicates mainly via grayscale dot/title | Read in code: IdentityChip label is app/model; state dot no textual accessible state. Participant title tooltip is not robust keyboard/touch status. Sidebar room dots similarly lack explicit state text. |

Positive evidence: interactive elements largely real buttons; icon actions have
aria-labels; forms use wrapping labels; global focus-visible outline exists
(styles.css:119–125); message Reply becomes visible on focus (:728–729); reduced
motion rule exists. Composer textarea overrides outline (:800), but parent
focus-within border (:758) supplies a focus cue—test its specificity/contrast,
do not claim there is no focus indicator. Native Dialog uses showModal, so basic
modal behavior exists; palette uses a nonmodal open attribute and lacks that behavior.

Other issues: palette cursor is only CSS active (no active-descendant/selected
semantics); global Cmd/Ctrl+K can open palette while modal is active; Escape globally
clears reply/search; no explicit return-focus policy; aria-live=polite wraps whole
conversation (potential repeated announcements). Earlier narrow-nav and initial-close-
button focus findings remain. No screen reader, native webview or touch test performed.

## 6. Tests that would catch these failures

| Test layer | Cases to add | Failures covered |
|---|---|---|
| Frontend unit/component | Delayed snapshot A after B; room generation changes; unmount pending operation | P6-01/02, stale room/status regressions |
| Form integration | Pending/failed/sent/unknown outbox response; permanent enqueue rejection; lost response then identical retry; close/reopen another dialog | P6-06 and protects first fix batch |
| Browser keyboard/AX | Palette input and row Escape, Tab bounds/return focus, named dialogs, presence accessible text | P6-08/09/11 |
| Browser contrast/viewport | Computed theme colors on actual backgrounds, small text, 600px rail and native min-width | P6-10 and P3 narrow issue |
| Contract | Typed action schemas + backend fixtures, native allowlist, error key collision | Wrong keys/types and preview/native gaps |
| Backend fault injection | Offline remove → reconnect; persisted removal intent; self-report age policy | P5-01/02 |
| End-to-end synthetic | Board posts with agents → delivery/report/sync/ack; counts; rejected workflow edit | Protects P3-01/02 fixes, catches UI/back-end integration gaps |

Current 187 pytest cases cover protocol/delivery/recovery and allowlist source parity;
TypeScript compile checks types only. package.json has no frontend test script.
Review browser scripts are evidence scaffolding with local tool paths, not a CI test
suite. Three added test methods in the fix batch are inherited across existing test
classes; raw count increase is not fifteen distinct new scenarios. Use reusable,
assertion-based frontend tests rather than relying on “no script error” as correctness.

## Priority / limits

Fix state ordering and offline removal before splitting every component. Add API and
operation lifecycle tests, then extract views without changing behavior. Accessibility
palette/dialog/contrast batch can be a separate bounded PR. Keep larger redesign out.
No architectural change, installed bundle build, or live data access performed.
Next Phase 7 synthesizes all reviews and marks already-fixed findings separately.

Verification: python3 -m pytest tests -q → **187 passed in 26.29s**; desktop tsc --noEmit → **exit 0**, no output.
