# B2 — ordered snapshots (R02 / R07)

2026-09-19. Source/dev-preview fix only; no installed-app rebuild/replacement or live-data access. Based on phase6-architecture.md P6-01, its phase6-browser.cjs NEWER → OLDER repro, and phase1-environment.md’s cold-helper/setup observation.

## Implementation

- A small snapshot controller owns request sequence and room generation. Only the latest request in the current generation may apply success **or failure**.
- Interval polls are single-flight; explicit post-action/retry refreshes can supersede a held poll. A superseded hung request cannot block later polling.
- Room-select and room-create invalidate outstanding reads before the mutation, suspend reads while it runs, and refresh after settlement. Concurrent room mutations are rejected before sending to the helper (whose selected room is global).
- Successful room changes establish the expected room from the API result. A current response for a different room is rejected and retried on the polling interval. A failed mutation refreshes authoritative state too, since a response can be lost after the helper commits. Cleanup invalidates pending results.
- Configuration is unknown until a successful snapshot. Cold helper failure renders unavailable with automatic polling and a retry button, never first-run setup. Setup appears only after a successful unconfigured snapshot. Dismissing the error banner does not clear unavailable health. Last confirmed content remains on failure.

## Regression evidence

- tests/snapshot-controller.test.mjs: **11 passed, 0 failed**. Deferred promises prove older success/failure ordering, newer failure preservation, recovery, single-flight polls, room invalidation during/after mutation, concurrent room mutation rejection, wrong-room rejection, failed-mutation refresh, superseded hung polls and cleanup.
- tests/snapshot-browser.test.mjs: **6 passed, 0 failed**, real headless Chrome DOM with synthetic /control responses. Held old success and failure cannot replace a newer post-action snapshot; held old-room data cannot undo room-select or room-create. Cold failure never shows setup (including after dismissing the banner), then normal polling recovers to either the configured room or confirmed first-run setup.
- python3 -m pytest tests -q: **198 passed in 26.60s**.
- apps/desktop/node_modules/.bin/tsc --noEmit: **exit 0**, no output.

## Re-run

Node >=22.18 is required for the controller’s TypeScript import. From the repo root:

```bash
node --test tests/snapshot-controller.test.mjs
PLAYWRIGHT_MODULE=/path/to/playwright node --test tests/snapshot-browser.test.mjs
python3 -m pytest tests -q
(cd apps/desktop && node_modules/.bin/tsc --noEmit)
```

The two Node commands also have test:snapshots and test:snapshots:browser package scripts in apps/desktop. Browser tests require an existing Playwright installation and Chrome (BROWSER_CHANNEL can override the channel); no new dependency was added. They own/stop Vite on port 1431, intercept every control request, and point its fallback ready-file location at a nonexistent path. No helper/profile/keychain is used. The local run used the pre-existing Node/Playwright installation noted in PICKUP.

## Boundaries

No B3 dialog-completion, busy tracking, recipient or draft policy changes. Backend snapshot schema validation, request timeout/error contracts, and native runtime verification remain outside B2. A never-settling current browser fetch has no new B2 timeout; explicit refresh can supersede it (B6 owns bounded requests). This is client request ordering, not a server revision protocol across independent clients. Stop before B3; owner controls deployment and the next authorization.
