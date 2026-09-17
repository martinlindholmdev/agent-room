# Result — Agent Room redeploy + autonomous coordination test (2026-09-17)

## STEP 1 — rebuild (done, verified)
Rebuilt `feat/overnight-build` (HEAD `4132f0b`, core fix `f51cd4d`). PyInstaller helper +
`tsc` (clean) + `vite` + `tauri build` all green. `codesign --verify --deep --strict`: valid.
Verified the fix is really in the bundle: `room_wait` is in `TOOLS`, advertised in `tools/list`,
handled in `tools/call`; board fan-out present in `node.py` `route_cache`; `wait_next` is
cache-seq based so board posts wake residents. New bundle:
`apps/desktop/src-tauri/target/release/bundle/macos/Agent Room.app` (built 13:50).

## STEP 2 — cutover (owner ran it; the exact prior script did not exist in the repo)
Assembled `docs/handover-2026-09-18/cutover.sh` (reversible: old bundle + data dir backed up to
Desktop). Owner ran it successfully: new app live on port 60839, fresh data dir, helper from
`/Applications`.

## STEP 3 — reconnect (done)
Created host `M1` (online) and bound the three agents in `general`:
codex-queue (`01a0a031…`), opencode-bridge (`ses_f591ad838ffec0vyPMEKm4Y5tf`), pull/Forge
(`forge-main`, glm-5-3). Codex and Forge bound but their agent processes were not running
(Codex out of usage until ~Sep 21; Forge not launched). **OpenCode reconnected live.**

## STEP 4 — autonomous coordination test (PASS)
Two residents connected through the **generic MCP connector** via the real self-service flow
(`room_connect` → pending → host approve → connected), zero bespoke code: `demo-a` (driven by me)
and `demo-b` (an independent subagent that composed its own replies). A third participant, the
**live OpenCode session**, joined on its own.

Proven, with no human driving after two board kickoffs:
- **Board fan-out wakes residents** — a board post (no recipient) woke `demo-b` while it was
  blocked on `room_wait`, and also woke the live OpenCode session. This is the exact
  "hey everyone reached nobody" bug, now fixed.
- **Agents reply on their own** — `demo-b` (subagent) and OpenCode negotiated a merged "step 2"
  over ~8 turns and then executed a directed-message sub-test between themselves.
- **`reply_to` threading** — every non-kickoff message carried `reply_to`.
- **Receipts reach `acknowledged`** — OpenCode acknowledged 5/5 of its received messages (clean
  chain); `demo-b` acked each message before replying. The `unavailable` receipts are `demo-a`'s
  inbox (my hand-driven side, which intentionally did not run the ack step) — expected pull
  "unread" state, not a delivery failure.

Full transcript: `coordination-test-transcript.txt` (this folder).

Left in place for inspection: the two `mcp` test puppets `demo-a`/`demo-b` (removable in-app).
Nothing pushed or merged.
