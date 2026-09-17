# Agent Room — overnight build handover, 2026-09-17

Branch `feat/overnight-build` (off `feat/persistent-agent-room-app`). Nothing pushed, nothing
merged, installed app NOT rebuilt. The live app + its 3 bindings (Codex, OpenCode, Forge) were
never modified by the build. **148 tests pass; `cargo check` on the Tauri crate is clean.**
Reviewed end-to-end by Fable (NO-GO → all blocker/High findings fixed → GO for merge).

## What was built (9 commits, each audited)
1. `56ded8f` **Model identity** — optional per-session `model`, threaded request→approve→binding;
   `room_connect` gains a `model` arg + `AGENT_ROOM_MODEL`; UI shows `app · model`.
2. `b2e76d9` **Generic connector** — new `app=mcp`, self-identified (`--generic` +
   `AGENT_ROOM_NATIVE`/`--native`/`AGENT_ROOM_MODEL`), read-on-demand like `pull`. Any MCP
   client can join with no bespoke code. (Forge can later move from the `--claude-app` shim to
   this: `AGENT_ROOM_NATIVE=forge-main`, `AGENT_ROOM_MODEL=glm-5-3`.)
3. `eb6fab3` **Multi-room** — create/rename/select, per-room routing/cursors/snapshots,
   cross-room isolation, request-time room capture. Backward-compatible ('general' default).
4. `729e526` **Presence + disconnect** — self-reported `working/idle/blocked/done` + `room_status`
   MCP tool; `binding-remove` disconnect with local + hub + delivery cleanup.
5. `0b1dd62` **Redesign** (superseded by the revert below) — token system + light mode + identity chip.
6. `4a079b6` **Smart views + rollup** — sidebar "Needs you"/"Active" + per-room status dot.
7. `212dc9c` **Palette reverted to black-and-white** (your call) — original monochrome greys,
   no accent hue, in dark + light. All features kept.
8. `de5bcd0` **Fable fixes** — B1 IPC allowlist + parity test; H1 remove-race; H2 dual-room bind;
   H3 in-app dialogs (window.prompt/confirm don't work in Tauri); H4 schema version bump.
9. `e20206c` **Selected nav tweak** — no left-bar on the selected room/chat, just the hover bg.

## Test it now (no install needed)
Everything runs live at **http://localhost:1420** (dev preview), in black-and-white, both themes.
The Agent Room app had quit overnight; I restarted it, so the room is back with all 3 participants.

## Fable review — outcome
NO-GO caught a real blocker (the installed app's IPC allowlist hadn't been updated, so
multi-room/presence/smart-views would be dead in the *shipped* app though fine in the preview).
Fixed + guarded with a parity test. Verdict after fixes: **GO for merge.** Full review:
`scratchpad/fable-review.md`. Remaining **Medium** items to do *before wider use* (not blockers):
- M1 hub session hard-delete leaves ghost receipts on disconnect.
- M6 "Active" smart view is a counter only; "Needs you" count vs Inbox count can differ.
- M7 Connections/approval card don't show which room an agent will bind into.

## For you — the gated steps (attended only)
Not done overnight on purpose: the cutover rebuilds the helper binary → **breaks the Keychain
ACL (-25320) and disconnects the live room**, and a Tauri rebuild needs Node (absent here).
Runbook:
  1. `tsc --noEmit` in apps/desktop (frontend never compile-checked; Node was absent).
  2. (optional) address M1/M6/M7.
  3. Merge `feat/overnight-build` → main.
  4. `cd apps/desktop && ./node_modules/.bin/tauri build --bundles app` (PATH incl. ~/.cargo/bin;
     rustc 1.88 ✓; APPLE_SIGNING_IDENTITY=-).
  5. Quit Agent Room, replace /Applications bundle, `codesign --verify --deep`, launch.
  6. Keychain recovery + re-add the 3 bindings (procedure in VERIFICATION.md).

## Later (your note)
Send to Claude Design for the visual remake once features are tested. Styling kept minimal until then.
