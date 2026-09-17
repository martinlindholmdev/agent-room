# Agent Room — design system (Supabase-flavored, dark + light)

Direction pinned by the owner: keep the dark aesthetic, add a real light mode,
take inspiration from Supabase's design system. Execute with restraint (skill:
spend boldness in one place; chrome recedes, content carries contrast — Linear).

## Subject & job
A local-first mission-control room where coding-agent CLIs (Claude Code, Codex,
OpenCode, Forge, Cursor) are durable participants. The page's one job: at a
glance, know which agent/room needs the human now, and act on it. Audience:
a developer running several agents. Voice: plain, developer-native, calm.

## Color (CSS variables; dark default, light under [data-theme=light] / prefers-color-scheme)

Dark (Supabase-like layered near-blacks, hairline borders, one green accent):
- --bg:            #121212   (app background)
- --surface:       #171717   (panels/sidebar)
- --surface-2:     #1c1c1c   (cards, raised)
- --border:        #2a2a2a   (hairline)
- --border-strong: #383838
- --text:          #ededed
- --text-muted:    #a0a0a0
- --text-faint:    #6b6b6b
- --accent:        #3ecf8e   (Supabase green — primary actions, active)
- --accent-hover:  #34b87d
- --accent-weak:   rgba(62,207,142,0.12)  (selected row/badge bg)

Status (presence — equal LCH-ish weight so no hue reads heavier):
- --status-working: #3b82f6 (blue)   • --status-blocked: #f59e0b (amber)
- --status-done:    #3ecf8e (green)  • --status-idle:    #6b6b6b (grey)
- --danger:         #ef5b5b (decline/remove)

Light (Supabase light — clean, near-white, subtle grey borders, same green):
- --bg:#ffffff --surface:#fafafa --surface-2:#ffffff --border:#e6e6e6
  --border-strong:#d4d4d4 --text:#1a1a1a --text-muted:#5c5c5c --text-faint:#8a8a8a
  --accent:#24b47e (slightly deeper green for contrast on white) --accent-weak:rgba(36,180,126,0.10)

## Type
- Body / UI: Inter (clean grotesque; 400/500/600). System-font fallback.
- Mono / identity + data: JetBrains Mono or IBM Plex Mono — used for the
  participant identity chip (app · model), IDs, counts, timestamps. This mono
  usage is the developer-native texture Supabase leans on.
- Scale: 12 (meta), 13 (body/UI default — dense like a dev tool), 15 (section
  titles), 20/28 (page titles). Weight 600 for titles, 500 for labels.
- Restraint: sentence case everywhere; no all-caps except tiny eyebrow labels
  in --text-faint with +0.06em tracking.

## Layout (from research §4.1 — Conductor 3-pane + muxel rollup)
- Left sidebar (dim, --surface, quieter than content): pinned smart views
  ("Needs you", "Active") above the room list; each room row = name + rolled-up
  status dot + participant count; expands to participants.
- Main: the room's shared thread (messages + hand-off cards).
- Right rail (collapsible): contextual artifact (diff/plan/preview).

## Signature (the one memorable, repeated element)
The **participant identity chip**: a live status dot + app name + model in mono
(e.g. `● Forge · glm-5-3`, `● Codex · gpt-5.1`), status color driving the dot.
It is the atom repeated in the sidebar, participant list, thread author lines and
approval cards — it makes "app + model + state" the visual through-line of the
whole app (and directly answers the owner's "which app and model id" ask).
Everything else stays quiet so this chip and the green primary action carry the eye.

## Theming mechanics
- All colors as CSS custom properties on :root (dark) + `@media (prefers-color-scheme: light)`
  guarded by `:root:not([data-theme=dark])`, plus explicit `:root[data-theme=light]` /
  `[data-theme=dark]` for the existing Settings System/Light/Dark control.
- Wire the existing Settings theme control (System/Light/Dark) to set data-theme.
- Radius: 6px controls, 8px cards. Borders hairline (1px --border). Shadows: almost none
  in dark (use borders + surface elevation); very soft in light.
- Motion: subtle only (120–160ms ease on hover/selection); respect prefers-reduced-motion.

## Quality floor
Responsive to narrow widths, visible keyboard focus (2px --accent outline),
reduced-motion respected, AA contrast on text.
