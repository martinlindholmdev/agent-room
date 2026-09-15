# Desktop acceptance — 2026-09-15

## Installed candidate continuation at 07:20 Stockholm time

Code candidate `ef39a9aeecf74f1587cbbb645063d54e9fa70fff` is now built,
ad-hoc signed and installed. The native executable, frozen helper and bundled
OpenCode plugin/support hashes match the packaged bundle; DMG integrity passes.
50 Python tests, four JavaScript adapter tests, frontend build and a separate
OpenCode SDK-compatible TypeScript adapter check pass. A consistent backup was
verified and restored to a fresh disposable destination. All 35 pre-install
event IDs survived the complete app Quit/replacement/reopen without duplicates;
seven historical receipts remained acknowledged. Actual UI inspection covered
history, exact composer targets, context, Settings, final Claude prerequisite
and bundled plugin instructions. Window-close background delivery and the
installed-app login plist were checked. A real login and sleep/wake were not run.

A candidate Codex test message `4970803b-db3b-494a-b1d8-819cd6aa7f63` was
submitted to exact native task `01a0a031-04e2-70c3-9e59-7416bba3097b`;
there was no receiver acknowledgement or correlated reply at last check.
OpenCode's new bundled adapter was not reloaded globally because another
preserved tab was actively handling user work. Claude's existing native
conversation is provider-blocked, and Desktop custom-channel launch support
remains unproven. Two physical Macs and conditional legacy retirement remain
outstanding. Implementation is complete; full acceptance is incomplete.

The following sections preserve the earlier installed behavior and its real
receipt/reply evidence. They are historical relative to candidate `ef39a9a`.

Source: continuation on the local M1, macOS 26.5.2, arm64. Commands ran
unconfined under the available execution policy. Native app interactions used
computer-use tools. Real acceptance below used the existing conversations;
synthetic protocol tests are listed separately.

## Real installed app

Installed at `/Applications/Agent Room.app`; private profile at
`~/Library/Application Support/Agent Room`. Complete app bundles were replaced
while the app was quit, preserving the profile. The helper embeds Python; it
runs without an end-user Python/Node installation. Local ad-hoc signatures pass
`codesign --verify --deep --strict`. The final DMG passes `hdiutil verify`.
No Developer ID/notarization or signed automatic release endpoint is configured.

The earlier installed behavior was from `da866fa`, including the verified receipt fix and
reconnect-warning fix. The final `a186c2a` package adds corrected onboarding text
and bundled OpenCode setup files. The Mac locked before its final replacement
and visible check in the earlier run, so those last packaging/onboarding additions were not claimed
installed then. Installed and packaged helper executables had the same SHA-256
`83c293452de9039520a2727289c35a62bf76a3fcd62b6c3173885210d68e098b`.
The final installer was ready then; candidate `ef39a9a` has since received its native UI check.

Closing the window left the helper online. Start at login was enabled in the
native Settings page; the LaunchAgent points to the installed app with
`--background`. A real logout/login was not performed. The app supervises its
helper: a forced SIGKILL recovered in 13.17 seconds, retaining all 10 existing
event IDs without duplicates and preserving acknowledged receipts. A first
10-second observation window was too short; it was not counted as a pass.
Full application quit/reopen also retained the conversation. A stale reconnect
warning exposed during this check was fixed to clear after a successful refresh.

## Exact native conversations

| Client | Native identity | Evidence / state |
|---|---|---|
| Codex | `01a0a031-04e2-70c3-9e59-7416bba3097b` | Existing task received push, explicitly acknowledged and replied. |
| OpenCode 1.18.30 | `ses_f5e779100ffe8bGhqh3r7Lrs1D`, directory `/Users/irislindholm/Code` | Existing conversation received push, acknowledged and replied through the authenticated plugin. |
| Claude app / Code | `9d34bace-2f77-4479-9d95-f44af9caba7e` | Binding prepared, config replaced; live new-room receipt is not verified. See exact blocker below. |

Codex original desktop message `3e4b73fa-c216-43e7-9544-16de2a6ae5d5`, delivery
`fbc828f4c3df4b61826d508870d44878`, reply `ff1c2311-35ae-4553-9787-0cf55d5d83cc`.
After helper recovery, message `95b625c8-2bd4-45f3-8ee9-73f3e4339931` was also
acknowledged and received the correlated reply “Final-build recovery confirmed”.
The existing task used the bundled helper, not old room tools or model polling.

OpenCode was restarted through its supported Restart menu only after all
review turns showed completed responses. All five native conversation tabs
survived. Its SDK bridge connected automatically to the existing native session.
First message `fea1b5f2-15df-4038-805d-3bfdde62e576` received a real reply, but
acknowledgement failed: the model supplied optional `read_through: 0` without a
previously offered read page. This was a real bug and was not counted as passing.

The fix accepts zero as a cursor no-op. Exact delivery ownership remains required;
positive unread cursors still require a complete offered page. The regression
check exercises the actual local control identity/generation/lease boundary.
After installing that fix, retest `172b6a59-6be1-46c2-8dab-78f49186b5ce` reached
acknowledged revision 3. Reply `9c970969-7484-4df8-bdc3-0f8e16017739` came from
OpenCode binding `e001a2dd-d7e3-4d01-9b64-4fb2edabc400`, with matching reply_to
and text “OpenCode receipt and reply verified”. The earlier delivery was also
explicitly acknowledged by the receiving agent. No sender fabricated receipts.

## Real shared planning and review

The two existing agents also completed a bounded collaboration fixture through
normal desktop delivery and tools. Codex created `acceptance-plan` version 1 and
`acceptance-review` version 1. OpenCode read `desktop_room_context`, reviewed the
inline arithmetic fixture, and recorded version 2 with its exact reviewer ID,
checks, empty findings and `self_review: false`. Its correlated reply was “Shared
planning and review verified”; both request and reply deliveries were acknowledged.
Artifact SHA-256: `4ebcf3e4571f3ad78dfa31bc52e4c07da54e6c12a84ae56b6b3860fe32dde2ff`.
This proves workflow transport/provenance with two real agents, not review of the
app's code or a substitute for the blocked independent security re-review.
Automated tests separately verify that artifact changes invalidate old approval.

## Claude chronology: tool rejection and later provider block

1. Claude initially requested direct user confirmation because the setup notice
   came from Codex. Martin supplied that confirmation directly in the existing
   conversation. That authorization request is resolved.
2. At 00:27, Claude's following tool step was marked **Blocked**. It attempted to list the
   app's Contents/helper directory and find README files. The tool returned:
   “The user doesn't want to proceed with this tool use” and instructed Claude
   to stop and wait for the user. This was not labelled a cybersecurity rejection.
   The continuation did not rerun that operation elsewhere or send a bypass prompt.
   Claude responded normally at 00:30. Its calendar conversation was preserved.
3. At 00:39, after a different calendar-fix request, the same native conversation
   showed a separate Anthropic provider-blocked-session error with request ID
   `req_011Cf48oF3ppNZdvB7kKUhMA` and label `[bio]`. The cause is unknown.
   No further Agent Room prompt was sent into it and no replacement session was
   started to evade the block.
4. The separate earlier Agent Room security re-review stopped after a service
   flag for possible cybersecurity risk. There is no final independent security
   approval. This is separate from Claude's connection/tool rejection above.

Even after the rejected step is resolved, actual custom-channel acceptance in
Claude's Desktop host must be verified. A configured MCP or an emitted event is
not proof of model receipt. Do not start a replacement conversation or silently
claim CLI channel support proves Desktop support.

## Automated and build checks

- 47 Python tests pass after the optional-zero-cursor fix, including the original
  delivery regressions, desktop identity, scoped pairing, revocation, replay,
  generation/lease fencing, work/review provenance and backup restoration.
- 4 JavaScript adapter tests pass: exact existing session/directory, accepted
  submission versus receipt, lost response uncertainty and explicit reply contract.
- TypeScript check and Vite production build pass; Tauri release app builds.
- New reconnect-warning UI behavior and onboarding text are included in the app.
- App signing and DMG creation run without Finder automation. No signing secrets
  are committed or included in diagnostics.

Counts changed deliberately: 47 tests before cleanup; 46 after removing the
unused legacy relay and its test; 47 after adding the real OpenCode regression.
These counts do not claim live Claude or physical two-Mac acceptance.

## Cutover and cleanup

- Claude `~/.claude.json` Agent Room entry now runs the bundled helper with
  `--mcp --claude-channel`; no globally fixed session identity.
- Codex `~/.codex/config.toml` Agent Room entry now runs the bundled helper
  with `--mcp`; no old Python/8787 route in this entry.
- OpenCode's old global `mcp.agent-room` JSONC block was removed, preserving
  unrelated configuration. Its installed plugin derives native identity from
  the actual host session and uses the host's existing authenticated SDK client.
- The desktop entry point no longer offers a legacy service or relay. The old
  local-room connector/control routes were removed. Legacy v2 modules remain
  solely as regression fixtures in source and are not bundled in the app.
- Four superseded app backup copies were deleted from the build scratch directory.
- Current source directory was converted in place to a self-contained Git
  repository with all commits, freeing it from the old source repository's Git
  metadata. No source replacement or loss of uncommitted work occurred.
- Iris source and hidden project configuration contain no active Agent Room code
  or hooks. Stale A4/A5 and old-history pointers were removed from its current
  docs in commit `17c1afe`, pushed. Historical reviews and safety rules remain.
  No Iris runtime, credentials, family data or product behavior was changed.

**Pending final legacy retirement:** the old daemon, loaded old MCP processes,
`~/Library/LaunchAgents/com.agentroom.daemon.plist`, `~/.agent-room`, and
`/Users/irislindholm/Code/agent-room` remain pending the required Claude cutover.
Do not call full reset complete while these exist. The new desktop app and the
verified Codex/OpenCode routes do not depend on them. Inspect any old worktree
copies for ownership before removing them; current maintenance source is the
self-contained `work/agent-room-app` directory.

## External acceptance remaining

- Preserve Claude's rejected step and later provider block separately. Once a
  user-selected supported connection is actually usable, require a real
  new-room acknowledgement and correlated reply; CLI custom-channel support
  does not establish Desktop Code host acceptance.
- Complete the scoped old-service/process/source/data retirement after that check.
- A second physical Mac and private HTTPS hub route are required for real
  Mac-to-Mac delivery and sleep/wake acceptance. No Tailscale setup was present
  on this host. Synthetic two-device HTTP/offline/replay tests pass but do not
  establish physical-device acceptance.
- Developer ID credentials and a release service are required for notarized
  distribution and automatic signed updates.

Historical v2 acceptance is retained in [legacy verification](docs/legacy-verification.md).
