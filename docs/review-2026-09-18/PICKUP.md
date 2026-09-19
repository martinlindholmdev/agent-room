# PICKUP — B3 scoped actions/drafts implemented; stop before B4

Done: Review phases 1–7 and B1–B3 are implemented in source. B3 fixes R05/R06 with
per-room retained text/recipient/reply/draft IDs, dialog-instance completion guards,
and operation-set busy tracking. Bind/pair followups cannot replace newer dialogs.
Room mutations and pending actions are mutually exclusive because the helper uses
a global selected room. Draft retention is in-memory for this app session, not across restart.

Evidence: phase6-architecture.md P6-02 and phase3-results.md journey 08;
b3-scoped-actions-drafts.md describes implementation, tests and limits. **6 B3 state
+ 8 synthetic Chrome tests passed**; **17 B2 tests also passed**, combined **31/31**.
Full checks: **198 passed in 26.52s**, desktop **tsc --noEmit exit 0**. Browser tests
use intercepted control responses and isolated dev servers, not a helper or installed app.
B1/B2 evidence remains in b1-durable-disconnect.md and b2-ordered-snapshots.md.

Next: **Stop. B4 has not started.** In a fresh conversation, owner may authorize B4
safe workflow editing (R04, R09–R12). Read AGENTS.md, REPORT.md and this note; start
a fresh branch from updated main. Owner must choose review invalidation policy;
report recommends invalidation only when review artifact/version changes. Other
findings remain open; B6 owns action-local errors and timeouts.

Safety: No installed-app rebuild/replacement or live-data access. Owner controls deployment.
Never commit credentials, ready.json or work/ contents. gh is at ~/.local/bin/gh.
Existing Node toolchain: /Users/irislindholm/.local/share/opencode/integrations/playwright/node_modules/node/bin;
existing Playwright is alongside node under that node_modules directory. These are
pre-existing test tools, not reintroduction of a retired connector. Isolated helper
Python: work/venv/bin/python (not needed for synthetic browser tests).
