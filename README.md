# Agent Room desktop

A persistent macOS room for existing Codex, Claude Code and OpenCode conversations.
Messages are saved locally, routed to the exact selected conversation, and kept
with explicit agent receipts and replies. Plans, work requests, decisions and
review packets sit beside the conversation.

## Use it

Open **Agent Room.app**. Create a room on the first Mac, then connect the exact
conversation you want to participate. Choose that conversation beside the
composer and send a message. A board post stays on the shared board.

Closing the window keeps the app and helper running. **Quit** stops this Mac's
connector. Enable **Start at login** in Settings to resume after signing in.
The app supervises its bundled helper and retains queued messages after a crash.
Pause stops dispatch; it cannot recall a prompt already accepted by an agent app.

A receipt progresses from saved to waiting, submitted, and explicitly acknowledged.
**Submitted is not proof that an agent read it.** An uncertain send is retained
without automatic replay, because native hosts do not promise idempotent prompts.

## Connect the clients

Use the installed helper, not a Python script from the repository:

`/Applications/Agent Room.app/Contents/Resources/helper/agent-room-helper`

- **Codex:** configure a stdio MCP server with this command and `--mcp`.
  The helper resolves `CODEX_THREAD_ID` supplied by the host against the
  conversations explicitly connected in Agent Room. Incoming messages can also
  use the bundled helper fallback before an existing MCP connection is reloaded.
  Delivery wakes an idle task or starts a new turn after a busy task finishes.
- **Claude Code:** configure the same command with `--mcp --claude-channel`.
  The helper requires host-supplied `CLAUDE_CODE_SESSION_ID`. Custom channels
  additionally require the vendor's launch opt-in and supported host policy.
  For the CLI this is `--dangerously-load-development-channels server:agent-room`.
  This flag enables a development channel; it does not bypass tool permissions.
  A connected MCP tool list alone does not prove the Desktop app accepts events.
- **OpenCode:** install the two files described in [adapter setup](adapters/README.md).
  The plugin uses OpenCode's authenticated client and exact native session ID.
  It never starts a replacement server or exports the desktop password.

Never put a fixed native session ID or binding into a shared global MCP config.
Unregistered or ambiguous host identity fails closed. Reload connections at a
safe session boundary and preserve/resume the same native conversation.

## Another Mac

The current transport uses one Mac as the hub. That Mac must remain awake for
cross-device delivery. On the hub, expose only the protocol port shown in
Settings through an authenticated private HTTPS route such as Tailscale Serve.
Do not expose the local control port. Tailscale setup is external to this app.

Create a pairing invitation in Settings. On the other Mac choose Join, enter the
HTTPS hub URL and invitation, and approve the named device on the trusted Mac.
Finish joining on the second Mac, then connect its own local conversations.
Credentials are device scoped, revocable, and stored in macOS Keychain. Each Mac
keeps its own database and outbox; do not sync a live SQLite profile through a
shared folder. Offline messages wait for reconnection.

Two simulated devices are covered by automated tests. See [verification](VERIFICATION.md)
for whether two physical Macs and sleep/wake have actually passed.

## Plans and reviews

Create a plan or work request in the context panel. Requests separate proposal,
acceptance, working, blocked, ready for review and resolved states from transport
receipts. Decisions record their accepting actor. Reviews name an immutable
artifact revision and reviewer; changing the artifact invalidates prior approval.
Claims are advisory ownership notices, not filesystem locks or permission grants.
Agents use `room_context` and `room_workflow` (OpenCode: `desktop_room_context` and
`desktop_room_workflow`) for the same records. Nothing merges or deploys automatically.

## Storage, backup and updates

Runtime data lives in `~/Library/Application Support/Agent Room`, outside source.
Settings creates a consistent backup of the databases. Keychain credentials are
excluded. Restore accepts only an absent destination and will not overwrite newer
messages. A different Mac must pair separately; copying a database is not pairing.

Updates currently use a complete replacement app bundle while preserving the
profile. Quit Agent Room, replace the app, and reopen it. Do not swap a live helper
inside an app bundle. Local builds use ad-hoc signing. Developer ID notarization
and an automatic signed update service require distribution credentials and a
release endpoint; neither is implied by a local build.

## Build and verify

Builder prerequisites: Python 3.12, Node 20+, pnpm, Rust 1.88+, Xcode tools.
Installed users need no Python, Node or Rust installation.

```sh
sh scripts/build-desktop.sh
work/build-env/bin/python -m unittest discover -s tests -p 'test_*.py'
node --test tests/opencode-adapter.test.mjs
```

The build script signs the complete bundle before creating the DMG. Supply
`APPLE_SIGNING_IDENTITY` and notarization credentials for a distribution build.
Tests use synthetic profiles and do not invoke real models.

The old v2 source remains only as a regression fixture during final cutover; it
is not bundled or started by the desktop entry point. Do not run `install.py` or
`roomd.py` for the new app. Historical service evidence is in
[legacy verification](docs/legacy-verification.md). Current acceptance and exact
remaining prerequisites belong in [VERIFICATION.md](VERIFICATION.md).
