# B5 — Honest presence

Implemented 2026-09-19. Scope: R03 and R24 presence only. B6 not started.

## Evidence and policy

Based on [Phase 5](phase5-presence-leftovers.md), its isolated
[probe](phase5-probe.py), R03 in [REPORT](REPORT.md), and P6-11 in
[Phase 6](phase6-architecture.md). The owner selected five minutes and
“No recent contact”, with no automatic idle deletion.

- Persist independent state_reported_at and last_contact_at wall-clock timestamps
  in binding JSON. A work report updates both; agent tools, validated waits/watches,
  and bridge open/poll/heartbeat/send-result update contact only.
- Registration, helper synchronization, UI polling and restart do not count as
  contact. Rebinding preserves reports/timestamps; restart preserves them while
  retaining the existing connector-generation fence.
- At >=300 seconds since contact, show **No recent contact** separately from
  **Last reported: Working/Idle/Blocked/Done** and each timestamp's age. UI time
  advances independently of snapshot success. Recent contact is not process liveness.
- Missing/invalid/future contact timestamps show **Contact unknown**. New bindings
  have unknown work state, not invented Idle. Legacy work reports survive with
  **report time unknown**. Remote sessions lack this device-local evidence and show
  unknown, not a fabricated work report or availability.
- MCP/pull explicitly say **On demand · silence is expected**. Codex retains
  next-turn wording; bridge transport/receipt copy remains separate.
- Participants, Connections and message identities have ordinary accessible text,
  replacing status-only dots/tooltips. Room rollups say last reported work state;
  the old Active metric is now Reported working (includes old reports deliberately).
  Inbox counts and palette keyboard semantics remain outside this batch.
- No expiry removes bindings, hub participants, history or pending work. Explicit
  Remove remains the disconnection path; B1 behavior is retained.

## Executed validation

- python3 -m pytest tests -q: **211 passed in 27.07s**.
- Desktop node_modules/.bin/tsc --noEmit: **exit 0**, no output.
- node --test tests/presence.test.mjs tests/presence-browser.test.mjs:
  **10 passed, 0 failed** (5 pure formatting/boundary cases, 5 Chrome tests).
- B2/B3/B4 frontend suites: **45 passed, 0 failed**.
- Six new isolated Python tests cover no-contact registration/sync, independent
  read/report times, rebind preservation, simulated-day idle + helper restart,
  legacy records, validated waits/watches and bridge contact/invalid leases.
  Existing no-report expectations now require unknown instead of Idle.
- Chrome advances a synthetic clock over 299 → 300 seconds for MCP, pull,
  Claude channel and Codex, asserting independent work/contact text, accessibility
  tree text, retained participants and Remove controls. Remote unknown is covered.

Initial test run exposed a wrong test method name (expire vs expire_channels)
 and an old Idle expectation; both were corrected before the passing full run.
Browser tests intercept all control responses and launch their own Vite process
with a nonexistent readiness path. Python homes are temporary under ignored work/.
No native build, installed-app replacement, live data access, real process-death
observation or two-Mac/screen-reader certification is claimed.

Reproduce frontend tests using Node >=22.18, Chrome and an existing Playwright
installation via PLAYWRIGHT_MODULE, as for previous batches. No dependency install
or retired connector setup was performed.
