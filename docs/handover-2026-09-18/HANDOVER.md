# Handover — Agent Room: redeploy + autonomous coordination test (2026-09-18)

You are picking up a finished build that needs to be **deployed to the installed app** and
then **tested for real, autonomously**. Everything below is on branch `feat/overnight-build`
in this repo. Nothing is pushed or merged. The installed `/Applications/Agent Room.app` is
still the OLD build.

Repo: `/Users/irislindholm/Code/agent-room-app`

## Owner's instruction for this task
1. **Redeploy** so ALL of it goes live in the real desktop app in one shot: the generic
   coordination primitive (`room_wait`) **and** the frontend fixes (they're all already
   committed on `feat/overnight-build`).
2. **Run the coordination test autonomously via desktop access** — don't make the owner drive
   each side. Prove the core: an agent posts to the room, another agent receives it and replies
   **on its own**. It must be **framework-agnostic / plug-and-play** — the goal is "clone from
   GitHub → point any MCP agent at it → it participates autonomously."

## State (all on `feat/overnight-build`, 172 tests pass, `cargo check` clean, Fable-reviewed)
Commits, newest first: `f51cd4d` room_wait/wait-next + board fan-out · `62adabc` composer
(Enter sends, smaller) · `a7b0a01` drop hardcoded "General" title · `ce25218` review mediums
· `de5bcd0` review blocker+highs (allowlist parity, remove race, dual-room bind, dialogs,
schema v2) · `212dc9c` black-and-white revert · `4a079b6` smart views · `0b1dd62` (superseded)
theme · `729e526` presence+disconnect · `eb6fab3` multi-room · `b2e76d9` generic mcp connector
· `56ded8f` model identity.

Features now in the branch: model identity, generic `mcp` connector, multi-room, presence +
disconnect, smart views, black-and-white UI, and **`room_wait`** (the fix for the core bug —
see below). Frontend fixes queued for this deploy: no more hardcoded "General" title, Enter
sends (Shift+Enter = newline), smaller composer.

## The core fix that this deploy delivers (`f51cd4d`)
Before: pull/`mcp` agents had no way to listen between turns, and **board posts (no explicit
recipient) notified nobody** — so "hey everyone" reached no one. That's why the live test
failed. Now: a generic `room_wait` MCP tool (any app) blocks on the next room message via a
new `wait-next` control action; board posts fan out to all room members; the tool descriptions
teach the resident loop (wait → read → ack → reply → wait) so it's plug-and-play. Tests prove
a board/human post wakes a waiter and an agent's own post does not.

## STEP 1 — rebuild the bundle (from `feat/overnight-build`)
Toolchain note: `scripts/build-desktop.sh` wants Node+pnpm+Rust. In the prior session Node/pnpm
were NOT on PATH; the working manual path was: PyInstaller via a venv, then the opencode node +
the project-local bins. Exact commands that worked last time:
```
cd <repo>
python3 -m venv work/build-env && work/build-env/bin/python -m pip install -r requirements-desktop.txt
NODE=/Users/irislindholm/.local/share/opencode/integrations/playwright/node_modules/node/bin
export PATH="$NODE:$HOME/.cargo/bin:$PATH"; export APPLE_SIGNING_IDENTITY="-"
work/build-env/bin/python -m PyInstaller --noconfirm --onedir --name agent-room-helper \
  --hidden-import keyring.backends.macOS --hidden-import desktop.mcp --hidden-import desktop.recovery \
  --distpath apps/desktop/src-tauri/binaries --workpath work/pyinstaller desktop_main.py
cd apps/desktop && node_modules/.bin/tsc && node_modules/.bin/vite build && node_modules/.bin/tauri build --bundles app
```
Bundle lands at `apps/desktop/src-tauri/target/release/bundle/macos/Agent Room.app`; verify with
`codesign --verify --deep --strict`.

## STEP 2 — cutover (GATED: the owner runs this)
Writing to `/Applications` is blocked by the harness classifier ("Production Deploy"). Do NOT
try to run it yourself — give the owner the one-line script (it backs up to Desktop, swaps the
bundle, resets the keychain item whose ACL is tied to the old binary, moves the data dir aside
so the new helper re-inits cleanly, relaunches). The exact script is in
`docs/overnight-handover-2026-09-17.md` and was run successfully once already.

## STEP 3 — reconnect the agents (you do this, via the control API, NOT gated)
After launch the app is fresh (setup screen). Read `~/Library/Application Support/Agent Room/ready.json`
for `{port, token}` and POST to `http://127.0.0.1:<port>/control`:
- `{"action":"create","data":{"name":"M1"}}`
- `{"action":"bind","data":{"native":"01a0a031-04e2-70c3-9e59-7416bba3097b","app":"codex-queue","title":"Build the persistent Agent Room app"}}`
- `{"action":"bind","data":{"native":"ses_f591ad838ffec0vyPMEKm4Y5tf","app":"opencode-bridge","title":"agent-room repo review & project direction","directory":"/Users/irislindholm/Code"}}`
- `{"action":"bind","data":{"native":"forge-main","app":"pull","title":"Forge · glm-5-3","model":"glm-5-3"}}`
Do NOT re-add `claude-m1-live` — that was a test puppet.

## STEP 4 — run the autonomous coordination test yourself
Follow `docs/handover-2026-09-18/fable-coordination.md` (the design) and `room-wait.sh` (a demo
wait loop). Generic recipe: connect a resident agent that loops `room_wait`; have another agent
post to the room board; confirm the waiter wakes and replies with **no hand-driving**. You can
drive one side yourself via the MCP helper (`--mcp --generic`, `AGENT_ROOM_NATIVE=...`) as a
genuine resident loop, and prompt Forge to stay resident for the other side. Verify with a
read-only snapshot: senders alternate, replies carry `reply_to`, receipts reach `acknowledged`.
Prefer proving it as a code-level fixture first where possible (minimize the owner's load).

## Gotchas
- Cutover breaks the login-keychain ACL (err -25320) → the script's delete + fresh-data-dir
  handles it; you re-create M1 + re-add bindings (Step 3).
- Codex was out of usage until ~Sep 21 — test with Forge (glm/claude via ArcAI).
- Rebuild is required for any backend/frontend change to show in the installed app.
- Reference docs in this folder: `fable-coordination.md` (mechanism + recipe + ranked gaps),
  `fable-review.md` (full code review), `frontend-notes.md` (Codex-app look is the Claude
  Design target; Remove-button key bug to verify), `design-system.md`.
</content>
