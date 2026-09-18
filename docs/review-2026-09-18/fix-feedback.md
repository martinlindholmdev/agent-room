# First fix batch — receipt, save and connection feedback

Owner approved fixing P3-01–03 before continuing reviews 4–7. Review-so-far merged in PR #1.

- Board fan-out still reaches local resident delivery queues and supports local explicit acknowledgements. It no longer generates hub receipts that the protocol never allocated. Existing saved/failed reports are retired only when a cached board message proves there were no explicit targets; unknown sources and targeted failures remain untouched. No shared hub receipt semantics changed.
- Workflow saves query the persisted outbox result. Rejection remains in the editable dialog; only confirmed sent closes it. Pending saves show a check-status action after 12 seconds, retain the same payload/event ID across retries, and do not silently submit duplicates. A new narrow outbox-status action is allowlisted in Rust; its rejection detail uses reason, not the API error-envelope key. Closing the form stops its result from closing a later dialog.
- Failed snapshot refresh marks the snapshot offline. Header and notice distinguish helper failure from hub disconnection and stop promising local persistence when the helper is unavailable. Successful polling restores status.

## Verification

Python: 187 passed in 26.12s (three added test methods also execute through existing inherited test classes). TypeScript: tsc --noEmit exit 0. Initial allowlist parity failure caught and corrected; initial browser test caught error-envelope collision and was corrected before final verification.

Isolated helper work/fix-feedback only, real headless Chrome DOM interaction:
- 28 board posts, two bindings: zero failed receipt reports (previously 56).
- Invalid resolved-work save: dialog stays open, completion evidence required appears inline, field remains editable.
- Corrected evidence: dialog closes, work becomes resolved.
- Failed helper response: Local helper unavailable header and draft-retention notice. Recovery: Room hub connected.
- Assertion-based repeat check: fix-feedback-browser.cjs, using the existing isolated fixture.

Backend regressions cover legacy board-report cleanup, local board acknowledgements, preservation of explicit/unknown failures, and pending/rejected/confirmed outbox-status. Existing delivery, protocol and allowlist suites pass. No native app build/install or live-data migration executed; owner-controlled update required. No real external-agent delivery test in this batch.

Remaining findings from phases 1–3 stay open unless explicitly addressed above. Continue Phase 4 next, then 5–7 and owner-selected fixes.
