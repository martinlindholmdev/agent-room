# Phase 1 — the review environment (2026-09-18)

How to bring up the app for this review, plus what the three real user states look
like. No product code was changed. The installed app and
`~/Library/Application Support/Agent Room` were never touched.

## Bringing it up

Three things, from the repo root:

```bash
# 1. the test helper, on an isolated home (its own keychain entry)
work/venv/bin/python desktop_main.py --home work/desktop-test &

# 2. seed every view
docs/review-2026-09-18/seed.sh

# 3. the dev preview
cd apps/desktop && node_modules/.bin/vite --host 127.0.0.1
# then open http://127.0.0.1:1420
```

Two toolchain notes that cost time and are not in the handover:

- **The helper needs `work/venv/bin/python`, not `python3`.** The system
  `python3` (Xcode's 3.9) has no `keyring`, and `desktop/secrets.py` imports it
  at startup, so `python3 desktop_main.py --home …` dies with
  `ModuleNotFoundError: No module named 'keyring'` before it ever writes
  `ready.json`. The plan's command as written does not start the helper.
- Node is not on `PATH`; `vite` needs the prefix from `PICKUP.md`.

No keychain prompt appeared: the isolated home derives its own vault name from
the home path (`desktop_main.py` hashes the resolved root), so the live app's
entry was left alone as intended.

The Vite dev server proxies `/control` to whatever `ready.json` points at, and
its default is already `../../work/desktop-test/ready.json`, so no extra
configuration was needed.

## What the seed creates

`docs/review-2026-09-18/seed.sh` is repeatable: run it twice and you still get
two rooms and three agents. It reports each step as `ok` or `skip` rather than
failing, because the steps that cannot repeat (device setup, room create, each
object's version 1) are legitimately rejected on a second run.

| Thing | What is seeded |
|---|---|
| Node | "Review M1", host mode |
| Rooms | `General`, `Release work` |
| Agents | `codex-queue` (working), `pull` (blocked), `mcp` (idle, never connected — the quiet agent) |
| Connection request | one pending `pull` request, `seed-pending-01` |
| Messages | three board posts in `Release work` incl. a fenced code block, one board post and one agent-addressed message in `General` |
| Objects | plan, work request, review awaiting a verdict, accepted decision |

Two constraints worth knowing before Phase 2 writes any fixtures:

- `codex-queue` requires a **canonical UUID** native identity
  (`desktop/protocol.py:215`). A readable string like `seed-codex-01` is
  rejected with the generic 400.
- `work` needs an `owner` and `review` needs a `reviewer` that is an exact
  session **in that room** (`desktop/protocol.py:312`, `:322`), so agents must
  be bound before objects can be created.

To start from an empty app: stop the helper, `rm -rf work/desktop-test`, start it
again.

## The three user states

### Seeded (`/tmp/02-seeded-room.png`)

Every view has content. Room hub connected, both rooms in the sidebar, the
participants/plan/work/decision panels all populated.

### Empty, fresh home (`/tmp/01-empty.png`)

`snapshot` returns `configured: false`, one `General` room, everything else
empty. The app shows the two-step "Set up Agent Room" screen with **Create a
room** and **Join an existing room**. Reasonable, but two things are wrong on
this very first screen (both `clicked` and `read in code`):

1. The body text still offers to "Connect existing Codex, Claude Code and
   **OpenCode** sessions". OpenCode was retired 2026-09-18. First thing a new
   user reads, and it advertises a connector that is gone. (`main.tsx` setup copy.)
2. The status pill says **"Connecting"** on a node that is not configured and is
   not trying to connect to anything. `online` is `false` and `mode` is `null`.

The left nav (Inbox, Plans & work, Search, General, New room, Settings) is fully
rendered and clickable before setup, so the empty state is navigable into views
that cannot mean anything yet. Worth walking properly in Phase 3.

### Helper stopped (`/tmp/04-helper-down.png`)

`ready.json` is deleted on shutdown, the Vite proxy returns
`503 {"error":"Local helper unavailable"}`, and the UI shows a dismissible
banner **"Error: Local helper unavailable"**. The error does reach the user in
plain words, which is good.

But underneath the banner the app falls back to the **setup screen** — the same
"Set up Agent Room" first-run screen, offering "Create a room" for a node that
is already configured with two rooms and three agents. A user whose helper has
crashed is told, in effect, that their room does not exist. The UI cannot tell
"not configured yet" from "cannot currently ask", because both arrive as a
snapshot with `configured: false`. Phase 6 material.

## One real defect found while seeding

Not looked for — the seed run produced it. Recorded here so Phase 2/3 can place
it properly.

**Every board post to a room containing agents produces permanently failed
receipts.** After one clean seed run the outbox held **nine** failed rows, all
`receipt target does not belong to message`: three board posts × three bound
agents. Evidence: `both`.

The cause, traced in code:

- The hub only inserts `receipts` rows for messages that have **explicit
  targets** (`desktop/protocol.py:276`).
- The local node, for a board post with no targets, **fans out** to every other
  bound session in the room and routes a delivery for each
  (`desktop/node.py:451-465`).
- Each of those fanned-out deliveries then emits a receipt event, which the hub
  rejects, because no `receipts` row exists for that message/target pair
  (`desktop/protocol.py:284`).

Confirmed against the database: the one agent-addressed message has a receipts
row; the board posts have none.

It never clears. `sync_once` only retries rows in state `saved`
(`desktop/node.py:384`), so `failed` is terminal.

What the user sees (`/tmp/03-inbox.png`, `clicked`): the Inbox "Needs you"
section fills with identical rows reading **"Message needs attention"** and the
raw developer string *"receipt target does not belong to message"*, one per
board post per agent, with no explanation and nothing to click. Counts disagree
at the same time: the Inbox nav badge shows `1`, the "Needs you" heading and the
sidebar smart view show `10`, and `snapshot.needsYou` is `2`.

The Inbox row for a failed item renders `o.event.body.text` (`main.tsx:1330`),
but these failures are *receipt* events, whose body has no `text` — hence the
empty third line.

## Screenshots

Kept in `/tmp` (not committed; the repo is public and these show a seeded
window): `01-empty.png`, `02-seeded-room.png`, `03-inbox.png`,
`04-helper-down.png`. Re-create them by re-running the steps above.

## Not done in Phase 1

Both themes, narrow window and keyboard-only use are Phase 3 items and were not
exercised. The empty and helper-stopped states were each observed once, in the
default theme at 1440×900.
