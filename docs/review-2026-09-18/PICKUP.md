# PICKUP — B6 error lifecycle implemented; stop before B7

Done: Review phases 1–7 and B1–B6 are implemented in source. B6 fixes R08,
R10's remaining timeout portion, R19 and R20. Typed versioned control envelopes
separate result/error/health; browser and native requests are bounded at 8 seconds.
Only definite rejection unlocks correction. Uncertain workflow acceptance retains
its event ID; Check status is read-only and never re-enqueues. Scoped action errors
and independent operational health are visible without raw diagnostic credentials.

Evidence: [b6-error-lifecycle.md](b6-error-lifecycle.md) and its referenced Phase 6
trace. **79 frontend tests passed** (24 new B6 + all 55 prior B2–B5),
**219 passed in 30.12s** (python3 -m pytest tests -q), desktop
**tsc --noEmit exit 0**, native **cargo check --locked exit 0** with target under
work/b6-cargo. Chrome uses synthetic control responses; Python uses fake HTTP nodes
or temporary homes under work/. No installed-app/webview certification. Existing
bridge/protocol callers retain their legacy wire format. Prior notes retain
session-only draft/form-tracking limitations.

Next: **Stop. B7 has not started.** A fresh owner-authorized conversation may take
B7 Inbox consistency (R13, R14). Read AGENTS.md, REPORT.md and this note; branch
from updated main. Define Needs you scope and failed-item dismissal policy first.
Never automatically retry uncertain native sends. R24 palette semantics remain B8.

Safety: No installed-app rebuild/replacement or live-data access. Owner controls deployment.
Never commit credentials, ready.json or work/ contents. gh is at ~/.local/bin/gh.
Existing Node toolchain: /Users/irislindholm/.local/share/opencode/integrations/playwright/node_modules/node/bin;
existing Playwright is alongside node under that node_modules directory. These are
pre-existing test tools, not reintroduction of a retired connector. Isolated helper
Python: work/venv/bin/python (not needed for synthetic browser tests).
