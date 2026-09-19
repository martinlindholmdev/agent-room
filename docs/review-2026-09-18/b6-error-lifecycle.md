# B6 — Error lifecycle

2026-09-19. Scope: R08, R10 timeout portion, R19, R20. No B7 work.

## Evidence and implementation

Read [REPORT](REPORT.md), [Phase 6](phase6-architecture.md) sections 2–4 and its
catch ledger, plus the B4 enqueue rejection code and workflow regressions.
Confirmed by code trace: snapshot.error collided with action errors; dispatch
health shared a field cleared by successful sync; fetch lacked a deadline/status
check; callback catches were empty; Check save status called enqueue again.

- Extracted typed per-action requests/results and a discriminated version-1
  envelope. Renderer requests explicitly opt into this contract. Existing local
  MCP/bridge callers and /v1 protocol consumers retain their wire format.
  snapshot.error is data, not an envelope failure. Renderer validates the envelope,
  snapshot collection shape, health scopes and consumed result discriminants/IDs;
  this is not a full recursive domain schema (B16 remains separate).
- Browser request + body parsing and native invocation are bounded at 8 seconds.
  Browser fetch aborts on timeout; Rust HTTP and preview forwarding also have an
  8-second deadline. Late native completion is ignored, not cancelled: acceptance
  remains uncertain. Native and browser use the same decoder and safe codes.
  HTTP success-looking bodies on failure statuses are not accepted as success.
- Only proven non-acceptance permits editing. B4's no-persisted-event rejection
  stays explicit. Generic handler exceptions remain uncertain, including a
  ValueError after a side effect. Native failure before dispatch can be definite;
  network loss, timeout and malformed responses cannot establish rejection.
- Workflow status checks now only read the original event ID; neither automatic
  retries nor the Check status button re-enqueue. Each status check is bounded;
  polling has a 12-second wall-clock budget after enqueue/refresh. An uncertain
  or missing operation remains locked rather than silently creating a second
  change. Closing the form still ends its session-memory tracking; durable
  resumable workflow forms are not claimed.
- Independent sync, stream and delivery health clears only on recovery of its
  own loop. Health is visible without treating stream degradation as total
  disconnection or implying a native-send retry.
- Action errors retain their room/dialog-instance ownership and independent
  dismissal. A later success cannot erase another action's failure. Current
  dialog failures are inside the modal; old-dialog failures remain labelled
  outside it. Workflow owns its inline error. Unexpected callback/runtime/login
  failures are caught and visible. Diagnostic text is fixed, never raw exception,
  outbox error or receipt reason text; legitimate invitation fields are unchanged.

## Regression evidence

- 18 transport/contract tests: browser/native adapter parity, rejection vs unknown,
  timeout/no retry/late completion, hanging body abort, HTTP status, malformed
  envelope, snapshot health and credential-safe unexpected failures.
- 6 new synthetic Chrome cases: independent concurrent errors, modal visibility,
  unexpected post-send callback, health/recovery, hung enqueue and hung status
  with no re-enqueue. Prior B2–B5 fixtures now use the versioned envelope;
  B4 expectations deliberately changed from identical re-enqueue to status-only.
- 8 Python tests exercise real HTTP envelopes, legacy compatibility, authentication,
  post-side-effect uncertainty, sanitization and isolated per-scope health recovery.
- Full frontend run: **79 passed**, including all 55 prior B2–B5 cases.
- Full Python: **219 passed in 29.85s** (subsequent final checks recorded in PICKUP).
- Desktop TypeScript: **tsc --noEmit exit 0**, no output.
- Native source: **cargo check --locked exit 0**, target under work/b6-cargo.
  Initial check caught the Tauri async State requirement for a Result return;
  fixed by returning the envelope inside Ok. No bundle build or app launch.

Chrome uses synthetic responses; Python uses fake HTTP nodes or temporary homes
under work/. Native transport injection tests run the shared renderer adapter,
not an installed webview. No installed-app verification, replacement, live-data
access or real external agent send. No secrets or work/ contents committed.

Stop before B7. Inbox counts, event-kind labels and dismissal/retry policy remain
unmodified. Uncertain native sends are never automatically retried.
