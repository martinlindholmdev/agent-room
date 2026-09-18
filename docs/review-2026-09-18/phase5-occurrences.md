# Phase 5 — tracked occurrence ledger

Baseline 4a874df. Case-insensitive OpenCode scan across tracked text; generated binaries and ignored work/live data excluded. Every matching source line is listed by location, without copying historical IDs/credentials. Historical review mentions are evidence, not instructions to reconnect.

| File | Matching lines | Classification |
|---|---|---|
| AGENTS.md | 38 | Historical review / rules |
| README.md | 3, 55, 56, 87, 111 | Documentation (inspect as historical/current) |
| VERIFICATION.md | 16, 97, 128, 131, 136, 138, 141, 148, 175, 177, 188, 213, 233, 242, 254, 255, 262, 309, 318, 333 | Documentation (inspect as historical/current) |
| adapters/README.md | 1, 3, 5, 10, 12, 13, 14, 16, 29 | Documentation (inspect as historical/current) |
| adapters/agent-room-desktop.ts | 1, 6, 38, 71, 156 | Executable/source |
| adapters/agent-room-desktop/opencode-client.mjs | 1 | Executable/source |
| apps/desktop/package.json | 18 | Dependency metadata |
| apps/desktop/pnpm-lock.yaml | 24, 353, 367, 1144, 1147, 1151 | Dependency metadata |
| apps/desktop/src/main.tsx | 132, 790, 2180, 2205, 2220, 2244, 2245, 2260, 2264 | Executable/source |
| delivery.py | 48, 72, 77 | Executable/source |
| desktop/node.py | 228, 229, 240, 328, 332, 333, 456, 590, 847 | Executable/source |
| desktop/protocol.py | 211, 216, 217 | Executable/source |
| docs/claude-monitor-takeover-2026-09-16.md | 4, 28 | Documentation (inspect as historical/current) |
| docs/desktop-app-plan.md | 9, 41, 76, 86, 96 | Documentation (inspect as historical/current) |
| docs/desktop-app-research.md | 7, 8, 22, 24, 28, 32 | Documentation (inspect as historical/current) |
| docs/handoff-room-connect-2026-09-16.md | 23, 73, 74, 105 | Documentation (inspect as historical/current) |
| docs/handover-2026-09-18/HANDOVER.md | 42, 47, 69 | Documentation (inspect as historical/current) |
| docs/handover-2026-09-18/RESULT.md | 18, 20, 26, 30, 32, 35 | Documentation (inspect as historical/current) |
| docs/handover-2026-09-18/design-system.md | 9 | Documentation (inspect as historical/current) |
| docs/handover-2026-09-18/fable-coordination.md | 8, 26, 43, 52, 107, 164, 167, 300, 335 | Documentation (inspect as historical/current) |
| docs/overnight-handover-2026-09-17.md | 4 | Documentation (inspect as historical/current) |
| docs/plan-fully-functional-2026-09-17.md | 43, 44, 58, 112, 126 | Documentation (inspect as historical/current) |
| docs/review-2026-09-18/PICKUP.md | 5 | Historical review / rules |
| docs/review-2026-09-18/fix-feedback-browser.cjs | 3 | Historical review / rules |
| docs/review-2026-09-18/inventory.md | 127, 130, 221, 222 | Historical review / rules |
| docs/review-2026-09-18/phase1-environment.md | 83 | Historical review / rules |
| docs/review-2026-09-18/phase3-browser.cjs | 3 | Historical review / rules |
| docs/review-2026-09-18/phase3-extra.cjs | 3 | Historical review / rules |
| docs/review-2026-09-18/phase3-journeys.md | 34 | Historical review / rules |
| docs/review-2026-09-18/phase3-results.md | 10 | Historical review / rules |
| docs/review-2026-09-18/seed.sh | 140 | Historical review / rules |
| docs/review-2026-09-18/strings.md | 20, 120, 314, 322, 326, 330, 336, 416, 840, 853, 858, 1055, 1126, 1128, 1182 | Historical review / rules |
| docs/review-plan-2026-09-18.md | 109 | Historical review / rules |
| install.py | 128, 130, 131, 133, 150, 204 | Executable/source |
| tests/opencode-adapter.test.mjs | 3 | Test fixture |
| tests/test_desktop.py | 259, 291, 323, 344, 624, 629, 636, 651, 653, 656, 661 | Test fixture |

## Literal identity references

Search: claude-m1-live, canonical UUIDs, ses_ IDs, seed/demo/forge identity labels. Tests and documentation are not runtime injections. Locations only; do not reuse old identities.

| File | Matching lines |
|---|---|
| VERIFICATION.md | 16, 17, 77, 80, 81, 86, 122, 124, 125, 133, 135, 136, 138, 139, 149, 151, 185, 186, 232, 233, 234, 236, 237, 238, 245, 252, 253, 254 |
| docs/claude-monitor-takeover-2026-09-16.md | 10, 11, 39 |
| docs/handoff-room-connect-2026-09-16.md | 73, 74 |
| docs/handover-2026-09-18/HANDOVER.md | 68, 69, 70, 71 |
| docs/handover-2026-09-18/RESULT.md | 18, 19, 24, 25, 29, 32, 36, 42 |
| docs/handover-2026-09-18/fable-coordination.md | 9, 10, 11, 190, 201, 213, 214, 223, 235, 241, 243, 327, 329 |
| docs/overnight-handover-2026-09-17.md | 14 |
| docs/review-2026-09-18/inventory.md | 253 |
| docs/review-2026-09-18/phase1-environment.md | 52 |
| docs/review-2026-09-18/phase3-results.md | 316, 323, 328 |
| docs/review-2026-09-18/seed.sh | 83, 88, 91, 98 |
| docs/review-plan-2026-09-18.md | 110 |
| tests/opencode-adapter.test.mjs | 7, 8, 13, 18 |
| tests/test_delivery.py | 27 |
| tests/test_desktop.py | 259, 590, 624, 628, 629, 633, 636, 653, 656, 659, 661, 664, 786 |
| tests/test_desktop_mcp.py | 89 |
| tests/test_desktop_monitor.py | 71 |
| tests/test_recovery.py | 53 |

## Python import evidence

AST import statements across tracked Python files (no execution).

| Importer | Imports root legacy/shared module |
|---|---|
| desktop/node.py:12 | delivery |
| room_mcp.py:20 | delivery |
| roomd.py:23 | delivery |
| tests/test_delivery.py:12 | roomd |
| tests/test_delivery.py:13 | room_mcp |
| tests/test_delivery.py:14 | delivery |
