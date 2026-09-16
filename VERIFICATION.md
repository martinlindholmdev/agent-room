# Desktop acceptance — 2026-09-15

## Installed candidate 2026-09-16: self-service session admission (room_connect)

Frontend/helper candidate `e29427d` adds self-service admission: an unbound
session submits a `room_connect` request with a title, the human approves once
in the app, and the binding hot-activates in the same helper process with no
reconnect. Helper pending-mode, the `request-create`/`request-decide` control
actions, the Inbox "Connection requests" section, and the `desktop_room_connect`
adapter tool are covered. All 77 Python tests, all 4 adapter tests, `tsc`, and
the Vite build pass. The whole bundle was rebuilt (rustc 1.88, ad-hoc
`APPLE_SIGNING_IDENTITY=-`), the `/Applications` bundle replaced after Quit, and
`codesign --verify --deep` passes; the app launches and the room hub connects.
Keychain recovery was performed again (helper binary changed → error -25320);
the two real bindings were re-added — Codex `codex-queue`
(`01a0a031-04e2-70c3-9e59-7416bba3097b`) and the opencode-bridge session
(`ses_f591ad838ffec0vyPMEKm4Y5tf`, directory `/Users/irislindholm/Code`) — and
the earlier `new-claude-session-1111-2222` test binding and its requests were
removed.

The 8-step end-to-end flow passed at the control-API level against the installed
helper: pending-mode initialize, `room_connect` exposed, room tools refused
while pending, request submitted, request visible in `snapshot()`, approved via
`request-decide`, hot-activated in the same process without reconnect, and
`room_read` worked after. Browser UI verification then ran against the live
helper on port 1420: a synthetic `pull` request (`ui-verify-2026-09-16`) was
submitted through the dev-server `/control` proxy and rendered in the Inbox
"Connection requests" section with its title, description and native identity
and both Approve and Decline controls; **Decline** was exercised in the browser
and the request cleared, returning the Inbox to zero pending. The synthetic
request row was deleted afterward; the two real bindings remain intact and no
test requests remain.

## Installed candidate 2026-09-16: delivery visibility, palette and plans view

Frontend candidate `d149ca2` (installed bundle embeds `index-DUxlIgS6.js`)
adds three verified slices on top of `8abfc91`: composer target delivery
health with pre-send warnings for dead bridges, a ⌘K command palette covering
navigation, compose actions, messages, participants and objects, and a
first-class Plans & work page for plans, work requests, reviews and decisions.
All 61 Python tests pass unchanged; TypeScript check, Vite production build and
the ad-hoc signed Tauri bundle pass; the DMG re-packages and verifies. The
send→snapshot round trip through the installed helper was re-verified after
install. Browser verification of all three slices ran against the live helper
on port 1420 including a synthetic dead-bridge binding, a palette
navigation/creation flow and a plan create→list round trip; synthetic rows
were removed afterward.

**Keychain recovery after install:** replacing the app bundle invalidates the
login-keychain item ACL for the device credential (Security framework error
-25320: only the creating helper binary may read without a prompt). Resolution:
the stale item was deleted, device mode/name/room settings and hub device rows
were reset, and the new helper recreated its credential through the normal
`create` path. Room "M1" is host, online, with zero events; all pre-existing
room content had been cleared with user authorization before this rebuild.
**Consequence:** existing bindings were cleared and each conversation must be
reconnected once in the app. A future installer should carry the credential
forward with an ACL that survives updates, or migrate the token explicitly.

Historical records below are retained for the earlier candidates.

## Current installed candidate: Claude app pull acceptance at 10:48 CEST

Implementation candidate `c51ac6f3ad5d0089b535fb772d36af4c22bd0d46`
adds ordinary Claude app MCP access through `--mcp --claude-app`. It selects only
an opted-in `pull` binding matching the host-supplied native
`CLAUDE_CODE_SESSION_ID`; it does not advertise a custom channel or wake an idle
app session. The installed app and packaged bundle match for the native
executable, helper, and both bundled adapters. The complete bundle was replaced
after normal Quit, with the same existing Claude app conversation restored and
its MCP manager showing `Connected · 6 tools`. Local ad-hoc signature and DMG
integrity checks passed. See the current task's `BUILD-MANIFEST.json` for exact
artifact hashes and runtime provenance.

The user personally confirmed the pending bounded Agent Room test in that
existing Claude app conversation. Native session
`9d34bace-2f77-4479-9d95-f44af9caba7e` then called `room_read`, `room_ack`,
and `room_post` through ordinary app MCP, each with an error-free native tool
result. Its exact `pull` binding
`0c4b0ce3-7a04-4195-a065-6c5f0bbf53c2` was the sole target of test message
`32aa261a-bcd2-4c0b-ab0e-7e81b80ffcbc` (sequence 59). The initial pull-only
receipt at sequence 60 was `unavailable`, revision 0: registration was not
counted as receipt. The receiving binding explicitly acknowledged delivery
`876c0446aa20468490a382cf6f9f89c2` at 10:45:00 CEST (sequence 61,
acknowledged revision 1), then posted board reply
`fb775714-8ff8-4e0a-b8af-d399de7d878a` at 10:45:06 with exact `reply_to`
the test message and text `Claude app receipt and reply verified` (sequence 62).
The independent Astra evidence review corroborated the receiver attribution,
native tool metadata, receipt revision, and reply correlation. This is a passed
Claude app read-on-demand exchange, not evidence of unsolicited idle delivery.

At 10:48, the hub was online without an error, the outbox was empty, and all
58 pre-change event IDs remained among 62 unique events. There are 13
acknowledged receipts in total. A fresh supported backup
`backups/room-20260915-104809-23e62877` passed manifest-hash and SQLite
integrity checks. Builder verification at the implementation revision passed
52 Python tests, four OpenCode adapter tests, frontend typecheck and production
build, and native packaging. An independent Astra review of the exact
seven-file source diff found no actionable correctness or regression findings;
its separate evidence review passed the Claude pull exchange. Neither review
completes the earlier service-blocked comprehensive security review.

Full project acceptance remains incomplete. Unsolicited Claude idle push has
not been established. Physical logout/login and sleep/wake checks were deferred
by the user; a second physical Mac and approved private HTTPS route remain
needed for hardware acceptance. Legacy service and client retirement is still
pending a scoped cutover decision. The records below preserve results for
earlier candidate revisions and their historical observations. Their former
claim of a continuing blanket Claude provider block and pending Claude receipt
is superseded by the app acceptance above; no rejected operation was retried.

## Historical installed candidate records

## Installed candidate update at 07:39 CEST

Implementation remains code commit `ef39a9aeecf74f1587cbbb645063d54e9fa70fff`;
the installed and packaged candidate were unchanged. The installed native executable,
helper, and bundled adapters still match the package by SHA-256; bundle signature
and DMG integrity were rechecked. This update supersedes the pending live-client
and helper-recovery statuses at 07:20 below. The earlier records remain historical.

The original candidate Codex message `4970803b-db3b-494a-b1d8-819cd6aa7f63`
received an explicit acknowledgement at 07:32:09 and correlated reply
`75202965-ca73-4a16-83d9-4d94f30fc056` at 07:32:16 from its exact existing
native task `01a0a031-04e2-70c3-9e59-7416bba3097b`. The earlier `submitted`
state was only native queue acceptance; no duplicate was sent.

At an idle boundary, the bundled OpenCode plugin and its support module were
installed globally together (SHA-256 `da5166890d3a065a7b9bbe065a9d5cbd604a299daa0f9981cf4131f9a7d35cc3`
and `f4abea0b6669ea5d508e5385c390fae619df466a5ed2f0445aa6818d0162774a`),
then OpenCode used its normal Restart action at 07:34. All 75 persisted sessions
remained; one tab was visible before restart, and its blank draft remained blank.
The exact existing target `ses_f5e779100ffe8bGhqh3r7Lrs1D` was reopened
from the session list with directory `/Users/irislindholm/Code`. The new
installed-candidate message `89cdc2c6-8eb6-4f6a-a094-24e5cd4c158c` was
acknowledged by OpenCode and correlated reply `609e507c-7ff7-44ec-bd88-8475851a6d82`
was addressed only to Codex. Codex acknowledged that reply and sent correlated
message `0a3a5699-6fdf-4732-a098-4a718f70faa3` only to OpenCode; OpenCode
acknowledged it and posted terminal board reply `3907abdf-b3e2-4fb5-9140-3c2e1130b8c1`.
All three routed deliveries reached receiver-created `acknowledged` revision 3.
The independent Astra acceptance check confirmed the exact intended OpenCode
native session and routing exclusivity. The previously reviewed six-file code
patch is unchanged; the earlier service-blocked comprehensive security review
remains incomplete.

A forced crash of the installed helper recovered in 15.769 seconds at 07:37:32.
The same 53 event IDs and 11 acknowledged receipts remained with no duplicate
event ID; connector generations advanced from 8 to 9, and the OpenCode bridge
reconnected. A new post-recovery message `45e7f87a-72af-4bae-99ce-650b1c838efb`
was acknowledged at 07:38:44, followed by matching board reply
`0b3fd8cd-e99e-4743-88f4-aba658ae87d3` at 07:38:52. The room then had 58
events, 12 acknowledgements, and an empty outbox.

At 07:40, a supported consistent backup was verified and restored into a
fresh disposable destination; the live profile was not overwritten. All 35
pre-install event IDs remain among 58 unique current events, with 12
acknowledged receipts and an empty outbox.

Full acceptance is still incomplete. The preserved Claude native conversation
remains provider-blocked. Claude Desktop's documented CLI-equivalent launch
table does not include the custom-channel opt-in, so Desktop channel delivery
is not established; no message or workaround was sent into the blocked session.
The user identified this always-on M1 as the hub. Delivery depends on that Mac
being awake and signed in; the app's configured login item starts after sign-in,
so a reboot still requires signing in before room delivery resumes. Physical
logout/login and sleep/wake checks were deferred by the user. A second physical
Mac, access to it, and an approved private HTTPS route are still needed for the
hardware checks. Conditional retirement of the 206-record legacy profile and
five old loaded MCP clients remains pending Claude cutover.

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

**Legacy retirement completed 2026-09-16 (opencode, Martin-authorized):** the
v2 launchd daemon (`com.agentroom.daemon`, port 8787) was stopped and its
`~/Library/LaunchAgents/com.agentroom.daemon.plist` removed; the orphaned v2
`room_mcp.py` bridge still loaded by the resumed Claude CLI process was
terminated; `~/.agent-room` was staged byte-identically into the app backup
`backups/legacy-v2-20260915` (verified manifest, channel journals md5-equal,
daemon log copied) and then deleted; `/Users/irislindholm/Code/agent-room` and
its `work/agent-room` copy were deleted. No old v2 process, listener, login
item, data directory or source tree remains. The new desktop app, helper, hub,
login item and this self-contained `work/agent-room-app` repository are
untouched and running. Precondition satisfied: Claude app cutover was
confirmed earlier the same day (pull exchange verified above).

## External acceptance remaining

- Preserve Claude's rejected step and later provider block separately. Once a
  user-selected supported connection is actually usable, require a real
  new-room acknowledgement and correlated reply; CLI custom-channel support
  does not establish Desktop Code host acceptance.
- Complete the scoped old-service/process/source/data retirement after that check.
  (Done 2026-09-16 — see "Cutover and cleanup" above.)
- A second physical Mac and private HTTPS hub route are required for real
  Mac-to-Mac delivery and sleep/wake acceptance. No Tailscale setup was present
  on this host. Synthetic two-device HTTP/offline/replay tests pass but do not
  establish physical-device acceptance.
- Developer ID credentials and a release service are required for notarized
  distribution and automatic signed updates.

Historical v2 acceptance is retained in [legacy verification](docs/legacy-verification.md).
