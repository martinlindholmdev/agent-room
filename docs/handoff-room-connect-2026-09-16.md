# Handoff: self-service session admission (room_connect) — 2026-09-16, mid-install

For the next session picking this up. Everything is implemented and tested;
the work is at the **install/verification** stage. Last commit on main is
`1f5e578`; all changes below are UNCOMMITTED in the worktree at
`/Users/irislindholm/Documents/Codex/2026-09-14/review-and-fix-the-agent-room/work/agent-room-app`.

## What was built (complete, tested at code level)

Sessions connect themselves; the human approves once in the app. No manual ID
entry, no per-session MCP config surgery.

- `desktop/node.py` — `requests` table; `request-create` / `request-decide`
  control actions; pending requests in `snapshot()`. Validation mirrors
  `bind()`. Approval creates the binding via the existing proven `bind()` path.
- `desktop/mcp.py` — helper no longer exits when the session is unbound: it
  starts in **pending mode**. New `room_connect` tool (always exposed) submits
  the request with a title; a 2s activator thread **hot-activates** the binding
  after approval with NO reconnect; room tools refuse while pending with a
  clear room_connect hint; claude-channel push waits until admitted; Monitor
  tools refuse while pending.
- `adapters/agent-room-desktop.ts` (synced to installed
  `~/.config/opencode/plugins/`) — new `desktop_room_connect` tool.
- `apps/desktop/src/main.tsx` + `styles.css` — Inbox "Connection requests"
  section with Approve/Decline; counts merged into the sidebar badge and
  Needs-you empty state.
- `apps/desktop/src-tauri/src/main.rs` — `request-create`, `request-decide`
  added to the IPC allowlist.
- `tests/test_desktop.py` — 3 new RequestTests. **All 77 Python tests pass,
  all 4 adapter tests pass, tsc clean, vite build clean.**

## Verification already done against an installed build

The full bundle (helper + frontend `index-diXIIbak.js`) was built, installed,
and the 8-step end-to-end flow PASSED against the installed helper:
pending-mode initialize, room_connect exposed, room tools refused while
pending, request submitted, request visible in snapshot, approved via
`request-decide`, **hot-activated in the same process without reconnect**,
room_read worked after. Test binding `new-claude-session-1111-2222` (pull)
and test requests remain in the room data — clean them out (see below).

## Current state — BROKEN INSTALL, needs one clean rebuild

After that verification, two post-hoc edits were made and the install broke:

1. The refusal error message was improved in `desktop/mcp.py` (pending-mode
   hint). Helper rebuilt to `work/helper-rebuild/agent-room-helper`.
2. The helper was hot-swapped into the installed app — WRONG: `cp` lost the
   executable bit → Tauri setup hook panicked "Permission denied (os error 13)"
   on launch. A `chmod +x` + re-sign followed, but the app still fails to
   launch (likely Gatekeeper provenance after re-signing a bundle in place).

Also: `apps/desktop/src-tauri/binaries/agent-room-helper/` was being replaced
with the rebuild when work stopped — it currently contains the new helper
(`_internal` + executable binary), which is what the next Tauri build needs.

### The fix path (follow exactly)

1. Confirm `apps/desktop/src-tauri/binaries/agent-room-helper/agent-room-helper`
   is executable (`chmod +x` it and the binary inside if unsure).
2. Rebuild the whole bundle, no hot-swaps:
   `cd apps/desktop && ./node_modules/.bin/tauri build --bundles app`
   (needs `PATH` with `~/.cargo/bin`, rustc 1.88: `rustup default 1.88.0-aarch64-apple-darwin`,
   `APPLE_SIGNING_IDENTITY=-`).
3. Quit any Agent Room process, `rm -rf "/Applications/Agent Room.app"`,
   `cp -R` the new bundle, verify `codesign --verify --deep`, launch.
4. Keychain recovery will be needed AGAIN (helper binary changed → ACL error
   -25320): delete the
   `app.agentroom.desktop.f2f9c1b2afaf2f15d577c7e4` generic password, reset
   `mode/name/room/device/cursor` in device.sqlite3 settings + devices/rooms/
   sessions rows in hub.sqlite3, launch app, `create` with name M1 via the
   control API. Then re-add bindings: Codex builder
   `01a0a031-04e2-70c3-9e59-7416bba3097b` (codex-queue) and opencode session
   `ses_f591ad838ffec0vyPMEKm4Y5tf` (opencode-bridge, directory
   `/Users/irislindholm/Code`). Remove the `new-claude-session-1111-2222`
   test binding and any test requests from the previous verification.
   Full procedure recorded in VERIFICATION.md ("Keychain recovery after
   install", 2026-09-16 entry).
5. Re-run the 8-step end-to-end test (script is in the room messages from
   this session; steps 1-8 verified once already). Then browser-verify the
   Approve/Decline UI in the Inbox (vite dev server + AGENT_ROOM_READY).

## Remaining after install is healthy

- Restore the user-wide Claude entry in `~/.claude.json` (backup:
  `~/.claude.json.before-agent-room-removal-20260916`) — Martin APPROVED
  this: with self-service admission, unbound sessions (incl. Iris) see only
  room_connect and stay locked out until approved in the app.
- Commit + push everything (uncommitted list above), update VERIFICATION.md
  (new installed candidate, request flow evidence) and `adapters/README.md`
  (document desktop_room_connect / room_connect flow and the
  pending→approve→hot-activate lifecycle).
- Claude Monitor native acceptance still waits on a non-Iris Claude session
  using room_monitor_setup; see `docs/claude-monitor-takeover-2026-09-16.md`.

## Key facts

- Control API: POST `http://127.0.0.1:<port>/control` from
  `~/Library/Application Support/Agent Room/ready.json` (Bearer token).
- Installed app = ad-hoc signed; `spctl` "rejected" is normal; the launch
  panic was the missing exec bit, not Gatekeeper policy.
- Never hot-swap files inside the installed bundle; rebuild and replace the
  whole app, then re-sign happens in the build.
- Build toolchain: `work/build-env` (Python 3.12 venv, PyInstaller), node at
  `~/.local/share/opencode/integrations/playwright/node_modules/node/bin/node`,
  `./node_modules/.bin/{vite,tsc,tauri}` inside apps/desktop (no pnpm needed,
  node_modules is fully populated).
- Local main == origin/main at `1f5e578`; push after committing.