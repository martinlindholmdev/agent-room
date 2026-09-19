# B4 — Safe workflow editing

2026-09-19. Source implementation only; no installed-app rebuild, deployment or
live-data access. Evidence: inventory.md F1/F2/F3/F6, phase3-results.md review and
rejected-save journeys, fix-feedback.md, phase6-architecture.md P6-06.

## Changes

- **R04:** Existing review verdict/findings are sent unchanged for metadata edits.
  The reviewed identity is artifact + exact revision + base revision, consistent
  with the existing protocol. Changing any of these resets verdict to pending and
  clears findings. Incrementing the collaboration object's edit counter alone does
  not invalidate a review. The hub allows unchanged results to be carried forward
  by a human/non-reviewer, but still refuses forged/changed verdicts or findings;
  only the exact reviewer can issue results. Hub invalidation clears stale findings.
- **R09:** Existing owner/reviewer selects are disabled with an explanation. Missing
  active conversations remain explicitly displayed; payloads retain their IDs rather
  than reading disabled controls from FormData. New assignments remain selectable.
  Resolved work requires completion evidence before browser submission.
- **R10, enqueue slice:** Helper returns acceptance=rejected only for a validation
  failure when the exact event ID has no persisted outbox entry, checked under its
  lock. UI unlocks and rotates ID only for that explicit marker or terminal failed/
  cancelled status. Transport failures, generic errors, existing-ID conflicts, and
  errors after persistence remain uncertain. Retry retains the exact ID and payload.
  Saved/nonterminal statuses stay locked. The narrow marker survives both existing
  browser proxy and native JSON forwarding; native execution was not exercised.
  **Timeouts and broader API/error contracts remain B6, not fixed here.**
- **R11:** Claim palette results show scope, owner, lease expiry and conflicts in a
  read-only dialog, with no form/save path. Scope is searchable in the palette.
- **R12:** Empty-room Request a review explicitly opens a review packet.

## Verification

- tests/test_safe_workflow.py: 7 isolated regressions covering approved/changes
  requested/pending preservation, unauthorized result alteration, each identity
  field's invalidation, queue-full rejection, identical retry, conflicting ID,
  post-persistence failure and unexpected failure.
- tests/workflow-browser.test.mjs: 14 synthetic Chrome tests covering all B4 UI paths,
  including lost response, generic failure, terminal failure/cancellation and
  saved/unknown status. Responses are intercepted; no helper/profile is contacted.
- Combined B2/B3/B4 frontend run: **45 passed, 0 failed**.
- Full Python suite: **205 passed in 25.60s**.
- Desktop node_modules/.bin/tsc --noEmit: **exit 0**, no output.
- git diff --check: clean.

Browser tests use the pre-existing Node/Playwright toolchain documented in PICKUP;
package script test:workflows:browser supports PLAYWRIGHT_MODULE and BROWSER_CHANNEL.
No installed webview, real agent review, or external-Mac behavior was tested. Original
review findings remain historical evidence; B5 and other batches are untouched.
