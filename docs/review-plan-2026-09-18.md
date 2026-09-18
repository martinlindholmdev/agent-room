# Full UX, feature and code review of Agent Room — plan (2026-09-18)

**For:** Fable running in Forge, opened in `~/Code/agent-room-app`.
**Owner's ask:** go through every single thing a user can see or do in the app. Odd texts,
buttons that do nothing, naming, stale agents. Judge it as a user first, then explain each
problem from the code.
**Read `AGENTS.md` first.** Its hygiene rules apply to every phase below.

## Ground rules for this review

- **This is a review. Change no product code.** The only files you create are under
  `docs/review-2026-09-18/`. Fixes come afterwards, in batches the owner picks.
- **Never touch the installed app or its data.** Review the frontend in the dev preview
  against an isolated test helper (Phase 1).
- **One conversation per phase.** At the end of each phase: commit, push, and write three
  lines in `docs/review-2026-09-18/PICKUP.md` (what is done, what is next, anything blocking).
  The next conversation reads only this plan, `AGENTS.md` and `PICKUP.md`.
- **Every finding needs proof.** Mark each one `clicked`, `read in code`, or `both`.
  A button is only "broken" if you clicked it and watched nothing happen, or traced it to a
  missing or failing handler.

## Where things are

| Thing | Place |
|---|---|
| Whole frontend (one file) | `apps/desktop/src/main.tsx` (2 624 lines, about 63 buttons) |
| Styles | `apps/desktop/src/styles.css` |
| Views in the app | setup screen, Inbox, Objects, Room (one per room), Settings, command palette, dialogs, workflow panel, context panel |
| Native shell | `apps/desktop/src-tauri/src/main.rs` |
| Backend the UI talks to | `desktop/node.py` (control actions), `desktop/monitor.py`, `desktop/mcp.py`, `desktop/protocol.py` |
| Possibly leftover from the old version | `ui.html`, `roomd.py`, `room_mcp.py`, `delivery.py`, `adapters/` |
| Known open issues | `docs/handover-2026-09-18/frontend-notes.md`, `fable-review.md` |
| Design direction | `docs/handover-2026-09-18/design-system.md` (black and white, Codex-app calm) |

## Phase 0 — hygiene baseline (do this before anything else)

State found on 2026-09-18: `main` was **20 commits ahead of GitHub**, never pushed. Three
old local branches are fully merged.

1. `git status -sb` and `git log --oneline origin/main..main`. Report what you see.
2. If `main` is still ahead: ask the owner for a yes, then `git push origin main`.
3. Delete the merged local branches: `git branch -d feat/overnight-build
   feat/persistent-agent-room-app fix/session-delivery` (`-d` refuses if anything is unmerged;
   never use `-D`).
4. `git switch -c review/ux-2026-09-18`. All review files go on this branch.
5. Run the tests once and record the baseline numbers in `PICKUP.md`.

## Phase 1 — get the app running safely

1. Start a test helper with its own home: `python3 desktop_main.py --home work/desktop-test`
   (it writes `work/desktop-test/ready.json`). A separate home gets its own keychain entry
   (`desktop/secrets.py`), so the live app's entry is left alone. If macOS asks for keychain
   access, the owner clicks Allow. `VERIFICATION.md` shows how this was done before.
2. In `apps/desktop`: `node_modules/.bin/vite --host 127.0.0.1`, open `http://127.0.0.1:1420`.
   The dev server forwards to the test helper. If Node is not on PATH, see the toolchain note
   in `docs/handover-2026-09-18/HANDOVER.md`.
3. Seed it through the control API so every view has content: a room or two, two or three
   bound agents of different connector types (`pull`, `mcp`, `codex-queue`), one pending
   connection request, a few messages, one plan, one review, one decision, one agent that has
   gone quiet. Save the seeding as `docs/review-2026-09-18/seed.sh` so it can be repeated.
4. Also look at the **empty** app (fresh home, nothing seeded) and the app with the
   **helper stopped**. Both are real user states.

## Phase 2 — inventory: every control, one table

Go through `main.tsx` top to bottom and list **every** interactive element: buttons, nav
items, inputs, toggles, menu rows, palette commands, keyboard shortcuts, dialogs.
Write `docs/review-2026-09-18/inventory.md` with one row each:

`view | visible label | what it calls (handler → control action) | backend handler exists? | result when clicked | verdict`

Verdict is one of: works, works but confusing, does nothing, errors, dead (cannot be reached).
Also list the reverse: control actions in `desktop/node.py` that no button uses.
Known suspect to confirm: Settings → Connections → Remove (may pass the wrong key).

## Phase 3 — walk the app as a user

Do each journey in the browser, writing down every moment of friction, not only bugs:

1. First run: setup screen, naming the node, what the user is told to do next.
2. Connecting an agent: where the instructions are, the request appearing, Approve, Decline.
3. Reading and posting in a room: composer, Enter and Shift+Enter, replies, long messages,
   code, many messages, scrolling, unread markers.
4. Several rooms: create, switch, rename, remove, which room a new agent lands in.
5. Objects and workflow: plans, reviews, decisions. Create, open, change state, approve.
6. Inbox and smart views: what lands there, how it clears, counts that match reality.
7. Agents over time: presence labels, an agent going quiet, disconnect, remove, reconnect.
8. Settings: every row. Does it save, does it say so, does it survive a reload.
9. Command palette: every command runs and is named like the button that does the same.
10. Both themes, a narrow window, keyboard-only use, focus order, Escape closing dialogs.
11. Failure: helper down, slow reply, action refused. Does the user get told, in plain words.

## Phase 4 — texts and naming

1. Extract **every user-visible string** into `docs/review-2026-09-18/strings.md`:
   text, where it shows, verdict, proposed replacement.
2. Check one word per thing. Today the code and UI mix words like session, agent, connection,
   binding, resident, connector, node, room, board, object, workflow. Propose one glossary
   (user word ↔ code word) and list every place that breaks it.
3. Flag: developer words shown to users (`pull`, `mcp`, `native`, ids), hardcoded names,
   texts that lie about state, missing empty-state and error texts, inconsistent capitals
   and punctuation, tooltips that are missing or repeat the label.

## Phase 5 — stale agents and leftovers

1. Explain in plain words how presence is decided (`PRESENCE_LABEL`, `desktop/monitor.py`,
   `room_wait`) and when an agent should show as gone. Then test it: does a dead agent ever
   leave the list, and can the user clear it themselves.
2. Find every leftover: OpenCode (retired) in UI, code, adapters, tests and docs. Test puppets
   such as `claude-m1-live`. Hardcoded session ids. Old-version files at the repo root
   (`ui.html`, `roomd.py`, `room_mcp.py`, `delivery.py`): used or dead? Prove it with imports
   and the build script.
3. Old docs that now mislead (paths, retired features). List, do not rewrite.

## Phase 6 — how it is built

Short and concrete, tied to user impact:

1. `main.tsx` is one 2 624-line file with one `App` component. Propose a split (by view) and
   say what it would cost and what it would make safer.
2. State, polling and refresh: can the UI show old data, double-fire an action, or lose an
   error silently. Every `catch` that swallows an error is a finding.
3. UI ↔ control API agreement: parameter names, ids versus native keys, error shapes.
4. Accessibility basics: real buttons, labels on icon buttons, focus visible, contrast in
   both themes.
5. Test gaps: which of the things you found broken would a test have caught.

## Phase 7 — the report

Write `docs/review-2026-09-18/REPORT.md`, plain English, short:

1. Half a page: the state of the app as a user meets it. The five worst things.
2. All findings in one table, worst first:
   `ID | view | what the user sees | what should happen | cause (file:line) | severity | size S/M/L | proof`
   Severity: Blocker (cannot do the job), High (wrong or misleading), Medium (friction),
   Low (polish).
3. **Fix batches**: group findings into batches that each fit one conversation and one pull
   request (for example "dead buttons", "naming pass", "stale agents", "remove leftovers",
   "split main.tsx"). Order them. Mark what needs the owner's decision first.
4. What you did not manage to check, and why.

Then: open the pull request for `review/ux-2026-09-18`, merge it, run the done-check from
`AGENTS.md` and paste its output. **Stop there.** Do not start fixing. The owner picks the
batches, and each batch is its own branch, its own pull request, merged before the next begins.
