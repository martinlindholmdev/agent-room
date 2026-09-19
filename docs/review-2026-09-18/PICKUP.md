# PICKUP — B4 safe workflow editing implemented; stop before B5

Done: Review phases 1–7 and B1–B4 are implemented in source. B4 fixes R04, R09,
R11 and R12, plus R10's definite-enqueue-rejection slice. Review verdict/findings
survive metadata and object-version-counter edits; only artifact, exact revision
or base revision changes invalidate them. Existing assignments are fixed; resolved
work requires evidence; claims are read-only; the review opener is corrected.
Explicit rejection unlocks editing; uncertain acceptance retains exact ID/payload.
R10 request timeouts remain B6, together with broader error lifecycle/contracts.

Evidence: b4-safe-workflow.md and its references. **14 B4 synthetic Chrome tests +
31 B2/B3 regressions passed (45/45)**; **205 passed in 25.60s**, desktop
**tsc --noEmit exit 0**. Browser tests intercept control responses, not a live helper.
B1–B3 evidence and session-only draft-retention limits remain in their batch notes.

Next: **Stop. B5 has not started.** In a fresh conversation, owner may authorize B5
honest presence (R03, presence portion of R24). Read AGENTS.md, REPORT.md and this
note; start a fresh branch from updated main. Owner must choose stale threshold/
wording; do not auto-delete idle connections. Other findings remain untouched.

Safety: No installed-app rebuild/replacement or live-data access. Owner controls deployment.
Never commit credentials, ready.json or work/ contents. gh is at ~/.local/bin/gh.
Existing Node toolchain: /Users/irislindholm/.local/share/opencode/integrations/playwright/node_modules/node/bin;
existing Playwright is alongside node under that node_modules directory. These are
pre-existing test tools, not reintroduction of a retired connector. Isolated helper
Python: work/venv/bin/python (not needed for synthetic browser tests).
