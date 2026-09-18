# PICKUP — full UX/feature/code review (2026-09-18)

## Done

Phase 0 (hygiene baseline). Merged local branches deleted with `-d`
(`feat/overnight-build`, `feat/persistent-agent-room-app`, `fix/session-delivery`).
Branch `review/ux-2026-09-18` created and is where all review files go. Test baseline
recorded below.

## Next

Phase 1 — get the app running safely: test helper on an isolated home
(`python3 desktop_main.py --home work/desktop-test`), vite dev preview on
`http://127.0.0.1:1420`, then seed every view and save the seeding as
`docs/review-2026-09-18/seed.sh`. Also look at the empty app and the helper-stopped state.

## Blocking / needs the owner

Nothing blocking. The three Phase 0 blockers were cleared with the owner's go-ahead:

1. **`main` pushed.** `e29427d..f9a8bb0`, all 20 commits now on `origin/main`.
2. **`gh` installed.** No `brew`/`npm`/`port`/`mise`/`asdf`/`nix` on this machine, so the
   official release binary was used instead: `gh_2.101.0_macOS_arm64.zip` from cli/cli,
   installed to `~/.local/bin/gh` (v2.101.0). Already authenticated as `martinlindholmdev`
   via keyring. **`~/.local/bin` is not on PATH**, so `gh` needs
   `export PATH="$HOME/.local/bin:$PATH"` or the full path. No shell profile was edited.
3. **Branch base resolved.** `review/ux-2026-09-18` was branched from `docs/review-plan` so
   it contains its own rules (`AGENTS.md` + the plan, commit `7633db2`); that commit is now
   contained in this pushed branch and `docs/review-plan` was deleted with `-d`.
   `AGENTS.md` still reaches `main` only when this review branch is merged in Phase 7.

## Baseline numbers (2026-09-18, start of Phase 0)

| Check | Result |
|---|---|
| `python3 -m pytest tests -q` | **172 passed** in 26.27s |
| `node_modules/.bin/tsc --noEmit` (in `apps/desktop`) | **clean**, no output, exit 0 |
| `git status -sb` | clean tree, tracking `origin/review/ux-2026-09-18` |
| `git log --oneline origin/main..main` | empty (was 20 ahead; pushed this session) |
| `git branch --no-merged main` | only `review/ux-2026-09-18`, the active review branch |
| `gh pr list` | empty, no open PRs |

Toolchain note: Node is not on PATH. `tsc` only runs after
`export PATH="/Users/irislindholm/.local/share/opencode/integrations/playwright/node_modules/node/bin:$PATH"`
(v24.19.0), per the toolchain note in `docs/handover-2026-09-18/HANDOVER.md`.
