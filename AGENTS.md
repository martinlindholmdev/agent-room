# AGENTS.md — rules for any agent working in this repo

Open your session **in this folder** (`~/Code/agent-room-app`), never from the home folder.

## Repo hygiene (not optional)

Work is not done until it is on GitHub. "Committed locally" does not count.

1. **Never commit directly on `main`.** Start every piece of work with
   `git switch -c <type>/<short-name>` from an up-to-date `main`
   (`review/…`, `fix/…`, `feat/…`, `docs/…`).
2. **Commit small and often.** One logical change per commit, a plain message saying what
   changed and why. Stage files by name. Never `git add -A` or `git add .`.
3. **Push after every commit session**: `git push -u origin <branch>`. Do not end a
   conversation with unpushed commits.
4. **Merge through a pull request**: `gh pr create`, then when tests pass
   `gh pr merge --merge --delete-branch`. Then `git switch main && git pull`.
5. **Before you say "done", run this and paste the output in your final message:**
   ```
   git status -sb
   git log --oneline origin/main..main
   git branch --no-merged main
   gh pr list
   ```
   Done means: clean tree, nothing ahead of origin, no stray unmerged branches, no open PR
   that is yours.
6. **Tests before every PR**: `python3 -m pytest tests -q` and, in `apps/desktop`,
   `node_modules/.bin/tsc --noEmit`. Paste the real result. If something fails, say so.
7. **The repo is public.** Never commit tokens, `ready.json` contents, keychain values or
   anything from `work/`. Check `git diff --staged` before each commit.

## Hard limits

- **Do not rebuild, reinstall or replace `/Applications/Agent Room.app`.** It breaks the
  keychain and disconnects every live agent. Only the owner does that.
- **Do not touch the live app's data** in `~/Library/Application Support/Agent Room/`.
  Test against an isolated helper home under `work/` instead.
- Do not re-add OpenCode. It was retired 2026-09-18.

## How to work

- One conversation per brief-sized item. Start a new conversation for each phase of a plan
  and begin it by reading only the plan and the short pickup note, not every old document.
- Claims need evidence. "Works" means you ran it and saw it. "Broken" means you clicked it
  or traced it in code. Say which.
