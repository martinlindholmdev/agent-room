# PICKUP — full UX/feature/code review (2026-09-18)

## Done

Phase 1 (app running safely). Test helper runs on the isolated home
`work/desktop-test`, the Vite dev preview serves `http://127.0.0.1:1420` and proxies
`/control` to it, and `docs/review-2026-09-18/seed.sh` seeds every view repeatably
(2 rooms, 3 agents one per connector type, 1 pending request, messages incl. a code
block, plan/work/review/decision, one quiet agent). All three user states were
observed: seeded, empty fresh home, and helper stopped. Written up in
`docs/review-2026-09-18/phase1-environment.md`. Two notes for the next phase: the
helper must be started with `work/venv/bin/python`, not `python3` (no `keyring` in
the system 3.9, so the plan's command never starts it), and seeding surfaced one real
defect — every board post to a room with agents leaves permanently failed receipts
that show in the Inbox as "Message needs attention · receipt target does not belong
to message" (9 rows after one seed run), with three disagreeing counts (badge 1,
heading 10, `snapshot.needsYou` 2).

Phase 0 (hygiene baseline). Merged local branches deleted with `-d`
(`feat/overnight-build`, `feat/persistent-agent-room-app`, `fix/session-delivery`).
Branch `review/ux-2026-09-18` created and is where all review files go. Test baseline
recorded below.

## Next

Phase 2 — inventory: go through `apps/desktop/src/main.tsx` top to bottom and list every
interactive element in `docs/review-2026-09-18/inventory.md`, one row each
(`view | label | handler → control action | backend handler exists? | result when clicked |
verdict`). Also list control actions in `desktop/node.py` that no button uses. Known
suspect to confirm: Settings → Connections → Remove (may pass the wrong key). Bring the
environment up with the three commands in `phase1-environment.md`.

## Blocking / needs the owner

Nothing blocking for Phase 2. One thing to decide when the owner picks fix batches: the
failed-receipt defect above is a backend/protocol disagreement, not a UI bug, so it will
not fit in a frontend batch.

The three Phase 0 blockers were cleared with the owner's go-ahead:

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
