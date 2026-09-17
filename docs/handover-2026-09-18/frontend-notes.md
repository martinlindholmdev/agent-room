# Agent Room — frontend notes & fixes (for the Claude Design remake + next rebuild)

## Design direction (owner, 2026-09-17)
- Reverted the Supabase/green redesign → keep **black-and-white / monochrome** (done).
- Selected nav/room: no accent left-bar, just the hover background (done).
- **Target aesthetic: the Codex desktop app** — owner likes its clean grotesque **font**,
  minimal chrome, generous whitespace, muted sidebar, one calm centered prompt. Use this as
  the reference for the Claude Design remake (proper visual pass, done later once features are
  tested — do NOT hand-restyle piecemeal now).

## Frontend fixes applied (code; need a rebuild to appear in the installed app)
- Removed the hardcoded "General" room title headline — it showed "General" even in other
  rooms; the breadcrumb already names the active room. (commit on feat/overnight-build)

## Frontend issues to verify / fix in the next pass
- **Remove-connection button**: `binding-remove` only worked via {native, app}; a call with
  {id} returned `removed:false`. Check what key the UI Remove button (Settings→Connections)
  passes — if it passes the binding id, the button is a no-op. Fix `_resolve_binding_id` to
  accept the binding id, or have the UI pass native+app.
- (add more as testing surfaces them)

## Note
Frontend changes only appear in the desktop app after a full rebuild + reinstall (the gated
cutover). Batch these and do ONE rebuild rather than one per fix.
