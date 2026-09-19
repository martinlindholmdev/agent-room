# B3 — scoped actions and drafts (R05 / R06)

2026-09-19. Source/dev-preview only; no installed app rebuild/replacement or live-data access.
Basis: phase6-architecture.md P6-02 and API/operation ownership trace, plus
phase3-results.md journey 08 (draft survives room switch, empty recipient dropdown,
“Session is not active in this room”). Owner selected retained per-room drafts.

## Implementation

- An interaction-state module owns an in-memory map keyed by active room. Each draft
  retains text, exact recipient, reply event and idempotency ID independently.
  Switching/creating rooms selects that room's draft, without copy/reset effect races.
  Retention is for the app session, **not disk persistence across restart**.
- All composer entrypoints use the map: typing, Reply, cancel reply, Escape, Start a
  plan and palette participant selection. Payload edits (including target and reply)
  rotate the draft ID. Success clears only the unchanged source draft's text/reply;
  failure retains it. Recipient stays selected within its room.
- A retained inactive recipient has an explicit unavailable option. Send refuses it
  until the user selects an active recipient or Room board; no silent board fallback.
- Dialog instances have ownership tokens, including reopening the same kind. Generic
  success closes only its originating instance. Bind/pair completion cannot replace
  a newer dialog. Workflow instances are keyed by token and their close callback
  checks ownership, in addition to the existing mount guard.
- Busy derives from pending operation IDs; success/failure removes only its own ID.
  Overlapping actions remain busy until all settle. Send checks synchronous state
  to prevent a second handler racing the first render.
- The helper chooses the global room when accepting human-authored sends/objects.
  Room-select/create therefore cannot overlap pending actions, and actions cannot
  start during a room mutation. Rejection is visible; retry after settlement. This
  prevents an in-transit send landing in a newly selected room without a backend
  protocol change. Other actions may still overlap.

## Regression evidence and rerun

From repo root, Node >=22.18, existing Playwright and Chrome:

    node --test tests/interaction-state.test.mjs tests/snapshot-controller.test.mjs
    PLAYWRIGHT_MODULE=/path/to/playwright node --test tests/interaction-browser.test.mjs tests/snapshot-browser.test.mjs
    python3 -m pytest tests -q
    (cd apps/desktop && node_modules/.bin/tsc --noEmit)

B3 package scripts: test:interactions and test:interactions:browser. Browser tests own
Vite on port 1432, intercept all control requests and use a nonexistent ready-file
path. No helper, credentials, installed app, profile or keychain is accessed.

- **6 B3 state tests passed**: room isolation, payload IDs, source-only completion,
  newer draft preservation, dialog ownership, both completion orders and room/action
  exclusion (including rejected/duplicate cleanup).
- **8 B3 synthetic Chrome DOM tests passed**: two-room draft/target/reply round trip
  and send payload; old room-create success/failure after reopening; overlapping
  actions with failure; held send blocks room switch and retains failed draft;
  palette/Escape room scope; inactive recipient; late bind cannot replace new dialog.
- **17 B2 tests passed** unchanged (11 controller + 6 browser).
- Combined Node run: **31 passed, 0 failed**.
- Python: **198 passed in 26.52s**. Desktop TypeScript: **exit 0**, no output.

Initial browser runs exposed fixture mistakes (request data nesting and accessible
button names); corrected before the passing run. This is synthetic browser proof,
not native webview/deployment certification. Local tool paths are in PICKUP.

## Boundary

B4 has not started: workflow verdicts, assignment validation, enqueue recovery,
claim forms and review opener remain unchanged. B6 owns action-local errors and
request timeouts; a never-settling action can still keep busy set. This client's
room guard is not a multi-client helper room-revision protocol. Owner controls deployment.
