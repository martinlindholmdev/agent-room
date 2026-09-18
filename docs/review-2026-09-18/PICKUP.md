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

1. **`main` is 20 commits ahead of `origin/main` and still unpushed.** Phase 0 step 2 needs
   an explicit yes before `git push origin main`. Not pushed in this session — asked, no
   answer given, so nothing was pushed.
2. **`gh` is not installed** (`gh: command not found`). The pull-request steps and the
   `gh pr list` line of the AGENTS.md done-check cannot run as written. Needs either
   `brew install gh` or an agreed local-merge deviation.
3. **This branch is based on `docs/review-plan`, not `main`.** `AGENTS.md` and
   `docs/review-plan-2026-09-18.md` exist only on that branch (1 commit, `7633db2`, also
   unpushed), so branching from `main` would have produced a review branch that does not
   contain its own rules. Consequence: `review/ux-2026-09-18` carries that commit too, and
   whatever lands on `main` later will bring `AGENTS.md` with it.

## Baseline numbers (2026-09-18, start of Phase 0)

| Check | Result |
|---|---|
| `python3 -m pytest tests -q` | **172 passed** in 26.27s |
| `node_modules/.bin/tsc --noEmit` (in `apps/desktop`) | **clean**, no output, exit 0 |
| `git status -sb` | clean tree |
| `git log --oneline origin/main..main` | 20 commits ahead, unpushed |
| `git branch --no-merged main` | only `review/ux-2026-09-18` / `docs/review-plan` |
| `gh pr list` | cannot run — `gh` not installed |

Toolchain note: Node is not on PATH. `tsc` only runs after
`export PATH="/Users/irislindholm/.local/share/opencode/integrations/playwright/node_modules/node/bin:$PATH"`
(v24.19.0), per the toolchain note in `docs/handover-2026-09-18/HANDOVER.md`.
