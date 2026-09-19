# PICKUP — B5 honest presence implemented; stop before B6

Done: Review phases 1–7 and B1–B5 are implemented in source. B5 fixes R03 and
R24's presence portion. Last-reported work and contact have separate persisted
wall-clock timestamps. At five minutes, contact reads “No recent contact” without
changing the work report. Missing evidence is unknown; on-demand silence is
explicitly expected. Accessible text replaces presence-only dots/tooltips. No idle
connection is automatically removed. Remote evidence remains unknown, not liveness.

Evidence: [b5-honest-presence.md](b5-honest-presence.md) and its references.
**10 B5 frontend tests + 45 B2/B3/B4 regressions passed**; **211 passed in 27.07s**;
desktop **tsc --noEmit exit 0**. Chrome tests use synthetic control responses;
Python tests use isolated temporary homes under work/. No installed-app claim.
B1–B4 notes retain prior evidence and session-only draft-retention limits.

Next: **Stop. B6 has not started.** In a fresh conversation, owner may authorize
B6 error lifecycle (R08, R10 timeout portion, R19, R20). Read AGENTS.md, REPORT.md
and this note; branch from updated main. R24 palette semantics remain B8. Other
findings remain untouched; do not auto-retry uncertain native sends.

Safety: No installed-app rebuild/replacement or live-data access. Owner controls deployment.
Never commit credentials, ready.json or work/ contents. gh is at ~/.local/bin/gh.
Existing Node toolchain: /Users/irislindholm/.local/share/opencode/integrations/playwright/node_modules/node/bin;
existing Playwright is alongside node under that node_modules directory. These are
pre-existing test tools, not reintroduction of a retired connector. Isolated helper
Python: work/venv/bin/python (not needed for synthetic browser tests).
