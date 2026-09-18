# Phase 3 — browser journeys (2026-09-18)

## Method and scope

Owner explicitly requested continuing Phase 3 in the same conversation, overriding
the usual fresh-conversation workflow. No product code or installed app changed.

Executed real DOM clicks/typing/keyboard input in headless installed Chrome through
Playwright, using a fresh temporary browser profile. Frontend: Vite at 127.0.0.1:1420.
A browser route forwarded /control to a separate helper at work/phase3-clean, with
credentials kept outside browser JS. This substitutes the dev proxy transport, not
application responses. The helper was configured through the UI. API calls supplied
requests, many-message fixtures and presence; these are identified below.

Scripts: phase3-browser.cjs (17 scenarios) and phase3-extra.cjs (supplemental).
Results: phase3-results.md. Screenshot: phase3-narrow.png (600×800).
The main script expects a fresh unconfigured helper home supplied via REVIEW_HOME;
create it with work/venv/bin/python desktop_main.py --home work/<unique-home>.
It is not idempotent and should not be rerun against an existing test home.
The supplemental script intentionally uses the completed work/phase3-clean fixture.
PLAYWRIGHT_MODULE can override the local module path; this references existing
installed test tooling and does not reinstall or reintroduce an app connector.

Two preliminary harness runs had selector mistakes (exact accessible select names
included option text; duplicate Pause buttons) and a rerun collided with existing
fixtures. Those were harness errors, not app defects. The clean run completed all
17 scenarios without harness or page errors. Supplemental checks also completed.
No real external agent, second Mac, or installed native shell was exercised.

## Journeys

| Journey | What was exercised and observed | Proof / limits |
|---|---|---|
| 1 First run | Create a room asks for Device name. Entered Phase 3 review; reached General and empty composer. Setup still advertises OpenCode. No post-setup integration wizard. | clicked; backend configured by form |
| 2 Connect | Manually bound generic MCP session through Connect agent; setup details expose helper flags and native/binding identities. Created two requests via API; clicked Approve/Decline; requests cleared and only approved agent was bound. Both bindings landed in selected Browser journeys room. | clicked + fixture API; real MCP host onboarding not tested |
| 3 Messages | Enter submitted; Shift+Enter preserved newline; Reply generated source link. 28 messages including long text and fenced code rendered; long text did not overflow at 1440px. Scroll container ended at bottom (2712+633=3345). No unread text marker found. Code remained literal fenced text (zero pre/code elements). | clicked; 26 volume/code fixtures injected by API; no claim about sustained high-volume performance |
| 4 Rooms | Created Browser journeys, switched to General and back. Draft text survived; recipient select appeared empty while health warning said Session is not active in this room. No rename/remove UI found; backend rename exists (Phase 2). | both; did not submit the stale-target draft |
| 5 Workflow | Created plan, work, accepted decision and pending review. Opened work; saved resolved with no evidence: form closed but object stayed proposed; outbox said completion evidence required. Supplemental save with evidence reached RESOLVED. Opened existing plan via palette. | both; review verdict/agent approval not performed |
| 6 Inbox/views | 28 board posts × 2 agents produced 56 failed receipt items. After invalid work save, Needs you showed 57 while Inbox had no badge. Failed entries have no clear/retry control. Active is display-only. | both; visible rendered list and snapshot corroborated |
| 7 Agent lifecycle | API set reviewer working; waited 32s with no real agent process; state remained working. Clicked Remove then reconnected identical native session: binding vanished then reused same ID. | both; 32s observation only, not proof of indefinite persistence |
| 8 Settings | Dark survived reload; Light changed attribute; System removed attribute. Pause survived reload; resumed delivery. Backup succeeded but success appeared in role=alert error banner. Opened pairing invitation and returned to requests; setup details opened. | clicked; no proof values captured. Native login/revocation/multi-device approval not tested |
| 9 Palette | Clicked all ten static commands; navigation/form destinations matched. New forms all titled New request; type values work/plan/review/decision correct. Message command focused composer. Supplemental Ctrl+K, arrows/Enter and participant/object/message results exercised. | clicked; Meta+K not established by headless run; dynamic message scroll location not measured |
| 10 Themes/narrow/keyboard | Dark/Light/System exercised; 600px viewport body was 600px, main 536px. Escape closed dialogs. New room initially focused Close dialog, Tab moved to input despite input autoFocus. | clicked; not a complete keyboard-only journey, screen-reader or contrast audit |
| 11 Failure | Invalid Codex ID left connect dialog open with generic rejection. Injected 3s send latency disabled composer then cleared draft on success. Simulated helper error retained draft; dismissing error only hid it until polling. Supplemental actually suspended isolated helper with SIGSTOP then resumed with SIGCONT: unavailable banner while header still said Room hub connected. | both; timeout adapter limited request to 1.2s. Not a terminated-helper/relaunch test; no installed helper affected |

## Findings and causes

Paths below refer to apps/desktop/src/main.tsx unless stated otherwise.

| ID | Severity | User-visible problem | Cause / evidence | Proof |
|---|---|---|---|---|
| P3-01 | High | Normal board posts flood Inbox with failed receipts, no clearing action | desktop/node.py:439–467 fans out recipient-less posts to bindings; desktop/protocol.py:276–284 creates receipts for explicit targets and rejects unmatched reports. 56 failures from 28 posts with two bindings. | both |
| P3-02 | High | Save closes form even when requested state never takes effect | :478–498 act closes after enqueue success; :2425–2459 save; protocol.py:318–319 requires completion evidence later. UI field not required. Correcting with evidence works. | both |
| P3-03 | High | Header claims connected while helper cannot answer | :433–439 refresh failure only updates connectionError, preserves old snapshot.online; :720–725 status uses stale online. Reproduced with simulated error and actual isolated-process suspension. | both |
| P3-04 | Medium | Room switch keeps draft and stale recipient state while dropdown appears empty | :656–660 clears search, not target/text/reply; :1717–1730 options change to room-local sessions. Warning exposes stale target. No send attempted. | both |
| P3-05 | Medium | Request a review opens work request | :1481–1483 opens workflow without kind; :2417 defaults work. Browser observed type=work. | both |
| P3-06 | Medium | Inbox badge and Needs you disagree dramatically | :508 pending receipts vs :529–532 stuck/outbox-based count. Browser saw no Inbox badge versus 57 Needs you. | both |
| P3-07 | Medium | Reconnect confirmation says new session, but reuses identity | :2299 text versus protocol.py:219–235 reactivating matching native/app/device/room row. Browser reconnect observed same ID. Not a request to change identity semantics. | both |
| P3-08 | Medium | Code is difficult to read as literal Markdown fences | :1595–1598 renders text directly. Real fenced message, zero code/pre elements. | both |
| P3-09 | Medium | Quiet agent still claims Working | Self-report persists; node.py:286–294 and snapshot rollups do not expire it. Observed after 32s without an agent; longer expiry remains Phase 5 scope. | both |
| P3-10 | Low | Backup success looks like an error | :1030–1031 uses setError for success. Observed Backup saved in alert banner. | both |
| P3-11 | Medium | Connection setup contains retired option and manual developer instructions | :786,2176,2240 onward; onboarding and connection dialog observed. No retired connector installed. | both |
| P3-12 | Low | New-room dialog focus starts at close button, not name | Shared showModal/focus and input autoFocus interaction; observed activeElement Close dialog, then Tab to INPUT. Exact browser lifecycle cause not established. | clicked |

Additional screenshot finding **P3-13 (Medium, clicked)**: at 600px the sidebar narrows to an icon-width rail but still shows wrapping/clipped labels (Plans & work, room title, Settings). Body width alone passing is not sufficient: phase3-narrow.png visibly shows navigation text clipped. The screenshot also shows Needs you 85 after later lifecycle actions; 57 above is the earlier measured Inbox checkpoint, not a final count.

No fix made. Severity is user impact, not implementation size.

## Recommended next work: shorten the path to fixes

Owner emphasized this is their primary interface and asked when building starts.
Original schedule requires Phases 4–7 before fixes. Recommendation (not yet
approved): close/merge the review-so-far through a PR, then start a focused fix PR
for **board receipts + honest send/save/connection feedback**, with regression tests
and the same isolated browser repro. That first batch is more important than a
large component split or exhaustive string cleanup. Keep remaining audit items as
tracked follow-up rather than a prerequisite to every bug fix.

Subsequent candidate batches: stale recipients/wrong dialog/lifecycle wording;
then room controls and connection onboarding; then broader naming/retirement and
architecture work. Do not silently merge all of these into one implementation.

Source fixes and installed-app update are separate: AGENTS.md forbids the agent
from rebuilding/replacing /Applications/Agent Room.app or touching its live data.
Owner-controlled installation remains required even after a fix is merged.

## Explicitly not completed

Real external agent delivery/acknowledgement/verdict; two-Mac join/revoke flow;
native login startup; full keyboard-only navigation/focus trapping; visual theme
contrast assessment; prolonged presence expiry; exact new-message scroll behavior
while reading old messages; full review/decision update matrix; cold helper restart.
These limits prevent claiming every Phase 3 path is fully verified. All eleven
journey categories were visited; platform/agent-dependent subcases remain open.
