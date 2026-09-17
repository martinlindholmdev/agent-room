# Agent Room app — research and evidence

Research date: 2026-09-14. Primary documentation was read during planning. Product and architecture decisions in desktop-app-plan.md are recommendations inferred from these capabilities and the existing repository; they are not vendor promises.

| Source | Verified finding | Design implication |
|---|---|---|
| [OpenCode server](https://opencode.ai/docs/server/) | Existing clients use a server; starting serve creates another server. Basic auth is supported. prompt_async returns 204; session/message/status and event endpoints exist. | Connect to the existing server and exact session/directory. Separate submission from actual acknowledgement. Verify installed behavior before retrying or handling busy sessions. |
| [OpenCode plugins](https://opencode.ai/docs/plugins/) | Plugin context includes client and directory; lifecycle events include session creation, status and idle. | Candidate for opt-in new-session registration and event-driven integration, subject to installed-version validation. |
| [Claude channels reference](https://code.claude.com/docs/en/channels-reference) | MCP channel capability and notification deliver events into a connected session. Custom development channels require a launch flag; organization/allowlist constraints still apply. | Preserve existing sessions, accurately explain setup, and never promise a custom plugin alone removes vendor restrictions. |
| [Claude sessions](https://code.claude.com/docs/en/sessions) | Session management includes continuing/resuming conversations. | Verify the exact host/session resume path before restart. Documentation alone does not prove this active desktop session can resume through a different frontend. |
| [Tauri sidecars](https://v2.tauri.app/develop/sidecar/) | Tauri bundles external binaries for specific target architectures. | Package the existing Python service as a standalone helper; assess both Macs' architectures before distribution. |
| [Tauri autostart](https://v2.tauri.app/plugin/autostart/) | Startup plugin includes macOS LaunchAgent support. | Useful installation mechanism; separately test helper supervision, app quit semantics and persistence. |
| [Tauri updater](https://v2.tauri.app/plugin/updater/) | Update artifacts require signatures. | Implement verified updates with safe migrations; do not invent a release endpoint or put signing keys in source. |
| [Tauri macOS signing](https://v2.tauri.app/distribute/sign/macos/) | macOS signing/notarization requires distribution credentials and tooling. | Build a development app first; report external signing prerequisites honestly. |
| [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve) | Serve provides tailnet access to local services with HTTPS. | Private hub transport option. App identity/room authorization and durable messaging remain our responsibilities. |
| [OpenWork](https://openworklabs.com/) | Official product presents a local/remote agent workspace. | User-selected aesthetic/onboarding reference. Create original monochrome UI; no assumption about undocumented implementation internals. |

## Existing implementation evidence

Repository /Users/irislindholm/Code/agent-room, base 6137aad, main clean when planning began. README.md and VERIFICATION.md record 21 passing focused tests, exact-task Codex idle and busy next-turn receipts, and installed-service acceptance. The implementation already has durable pinned routes, explicit acknowledgement, conservative uncertain-send handling, and singleton recovery protection. Reuse these guarantees.

Actual Claude model receipt remained unverified in that record: an isolated test could not authenticate its model, despite MCP connecting. A separate live Claude owner is now investigating their existing session. This is not proof that their session shares the isolated test's authentication issue. OpenCode has no delivery adapter in the base. Shared-token loopback room authorization is insufficient for distinct paired-device trust.

## User-supplied OpenCode investigation

Astra reports verification against the existing session database, listening server authentication requirement and installed endpoint/body implementation. Astra did not obtain the password or send an authenticated probe. Exact session and temporary endpoint are in the separate local connection handoff, outside Git.

Reported discovery: await window.api.awaitInitialization() in OpenCode's renderer returns {url, username, password}. This is desktop IPC scoped to that renderer, not a public/unauthenticated HTTP endpoint. Both endpoint and secret can change on restart. This report is useful local evidence, not an independently tested stable public integration API. The builder must verify how an external connector can legitimately consume the connection locally; prefer supported plugin/client integration if available. Never display the returned object in logs or tool output.

## Open questions to resolve during implementation

- OpenCode busy-session semantics, correlation and actual idempotency; optional messageID does not by itself prove retries are safe.
- Secure desktop connection discovery without version-fragile code injection or requiring users to copy secrets each restart.
- Claude's current session channel receipt/resume outcome and any host policy limitation.
- Which Mac should host the hub and whether the second device is reachable for a real end-to-end test.
- Bundled helper size/startup behavior, installed Rust/Xcode availability, target architectures and signing resources.
- Compatibility/migration of existing private room state under the new protocol. Synthetic fixtures first, never commit live messages.

None of these questions requires suspending independent local UI, protocol or adapter-contract implementation. An unresolved live check must remain explicitly unresolved in release claims.
