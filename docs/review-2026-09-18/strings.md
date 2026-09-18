# Phase 4 — text and naming inventory

Source baseline: 5f6b126, after the first fix batch. **All proof: read in code.** No new browser claims or product edits.

## Extraction contract

AST scan of every JSX text node, quoted string and template in main.tsx. Whitespace normalized; repeated occurrences retained. Split JSX sentences retain fragments so every source occurrence is traceable. Includes helper maps, attributes, tooltips, palette descriptors, placeholders and status options. Dynamic data and external errors are catalogued separately. This is source coverage, not enumeration of arbitrary runtime values.

The conservative scan produced 941 candidates. Exclusions are recorded rather than silently counted as copy. Run extract-strings.cjs from repo root with Node on PATH.

Proposals on multi-part sentences are wording guidance for the assembled sentence, not literal search-and-replace patches. The glossary and claims sections qualify the occurrence table. “Keep” is an editorial verdict, not an execution claim.

## Visible copy

| Text | Where (main.tsx line) | Verdict | Proposed replacement |
|---|---|---|---|
| General | Identity/delivery :107 | Keep | Unchanged. |
| General | Identity/delivery :125 | Keep | Unchanged. |
| Codex | Identity/delivery :131 | Keep | Unchanged. |
| OpenCode | Identity/delivery :132 | Retired | Remove retired connector copy/option; describe supported connectors only. |
| Claude Code | Identity/delivery :133 | Keep | Unchanged. |
| Read on demand | Identity/delivery :134 | Mode not app identity | On-demand agent; show app/model separately when known. |
| MCP (any agent) | Identity/delivery :135 | Advanced precision | Keep protocol name in connector picker/setup; explain using the agent app’s tools. |
| · | Identity/delivery :138 | Keep | Unchanged. |
| Working | Identity/delivery :141 | Keep | Unchanged. |
| Idle | Identity/delivery :142 | Keep | Unchanged. |
| Blocked | Identity/delivery :143 | Keep | Unchanged. |
| Done | Identity/delivery :144 | Keep | Unchanged. |
| Session is not active in this room | Identity/delivery :158 | Naming | Conversation |
| On another Mac · delivery depends on that device being online | Identity/delivery :162 | Keep | Unchanged. |
| Read on demand · the agent reads when it is active | Identity/delivery :167 | Keep | Unchanged. |
| Wakes an idle task · arrives next turn if busy | Identity/delivery :172 | Unverified promise | Sent to the agent app; check delivery status. |
| Bridge not connected · message will be queued until it reconnects | Identity/delivery :177 | Developer term | Agent connection |
| Bridge active · routed to this conversation | Identity/delivery :179 | Developer term | Agent connection |
| Read on demand · awaiting agent | Identity/delivery :183 | Keep | Unchanged. |
| Waiting for device | Identity/delivery :185 | Keep | Unchanged. |
| Waiting for agent app | Identity/delivery :186 | Keep | Unchanged. |
| Submitted to agent app | Identity/delivery :187 | Keep | Unchanged. |
| Agent acknowledged | Identity/delivery :188 | Ambiguous | Agent confirmed reading |
| Needs connection | Identity/delivery :189 | Missing next step | Agent connection unavailable — check setup |
| Send uncertain | Identity/delivery :190 | Opaque | Delivery could not be confirmed |
| Saved on this Mac | Identity/delivery :191 | Keep | Unchanged. |
| Needs attention | Identity/delivery :192 | Keep | Unchanged. |
| Agent conversation | Palette :230 | Keep | Unchanged. |
| You | Palette :231 | Keep | Unchanged. |
| Go to room | Palette :236 | Keep | Unchanged. |
| Conversation | Palette :236 | Keep | Unchanged. |
| Navigate | Palette :236 | Keep | Unchanged. |
| Go to inbox | Palette :237 | Keep | Unchanged. |
| Needs you and waiting items | Palette :237 | Keep | Unchanged. |
| Navigate | Palette :237 | Keep | Unchanged. |
| Go to plans & work | Palette :238 | Keep | Unchanged. |
| Plans, requests, reviews, decisions | Palette :238 | Keep | Unchanged. |
| Navigate | Palette :238 | Keep | Unchanged. |
| Settings · connections and device | Palette :239 | Keep | Unchanged. |
| Navigate | Palette :239 | Keep | Unchanged. |
| Message the room… | Palette :240 | Keep | Unchanged. |
| Focus composer | Palette :240 | Keep | Unchanged. |
| Compose | Palette :240 | Keep | Unchanged. |
| New work request | Palette :241 | Keep | Unchanged. |
| Compose | Palette :241 | Keep | Unchanged. |
| New shared plan | Palette :242 | Naming | New plan |
| Compose | Palette :242 | Keep | Unchanged. |
| New review packet | Palette :243 | Naming | New review |
| Compose | Palette :243 | Keep | Unchanged. |
| Record a decision | Palette :244 | Keep | Unchanged. |
| Compose | Palette :244 | Keep | Unchanged. |
| Connect a conversation | Palette :245 | Naming | Connect agent |
| Compose | Palette :245 | Keep | Unchanged. |
| · message | Palette :257 | Keep | Unchanged. |
| Messages | Palette :258 | Keep | Unchanged. |
| · | Palette :267 | Keep | Unchanged. |
| Participants | Palette :268 | Keep | Unchanged. |
| Plans, work and reviews | Palette :279 | Keep | Unchanged. |
| Search messages, participants, plans or jump… | Palette :302 placeholder | Keep | Unchanged. |
| Command palette | Palette :303 aria-label | Keep | Unchanged. |
| esc | Palette :319 | Capitalization | Esc |
| No matches for “ | Palette :341 | Keep | Unchanged. |
| ”. | Palette :341 | Keep | Unchanged. |
| · | Shared dialog :365 | Keep | Unchanged. |
| Close dialog | Shared dialog :394 aria-label | Keep | Unchanged. |
| Agent conversation | App state :506 | Keep | Unchanged. |
| You | App state :507 | Keep | Unchanged. |
| Agent Room | Sidebar :587 | Keep | Unchanged. |
| 01 | Sidebar :588 | Ambiguous decoration | Remove brand build marker; retain numbered setup steps. |
| Inbox | Sidebar :595 | Keep | Unchanged. |
| Plans & work | Sidebar :607 | Keep | Unchanged. |
| Search | Sidebar :619 | Keep | Unchanged. |
| ⌘ K | Sidebar :619 | Keep | Unchanged. |
| VIEWS | Sidebar :623 | Capitalization | Sentence case in source; visual uppercase may remain styling. |
| Needs you | Sidebar :632 | Keep | Unchanged. |
| Bindings currently self-reporting as working, across all your rooms on this Mac | Sidebar :639 title | Developer term | Agents reporting Working across rooms on this Mac. |
| Active | Sidebar :642 | Ambiguous count | Working agents |
| YOUR ROOMS | Sidebar :649 | Capitalization | Sentence case in source; visual uppercase may remain styling. |
| New room | Sidebar :678 | Keep | Unchanged. |
| Sessions stay in | Sidebar :683 | Naming | Conversation |
| their own apps. | Sidebar :685 | Keep | Unchanged. |
| Settings | Sidebar :694 | Keep | Unchanged. |
| This Mac | Sidebar :698 | Keep | Unchanged. |
| Room | Header/errors :706 | Misleading breadcrumb | Remove fixed Room prefix outside a room. |
| Inbox | Header/errors :711 | Keep | Unchanged. |
| Plans & work | Header/errors :713 | Keep | Unchanged. |
| Settings | Header/errors :714 | Keep | Unchanged. |
| Local helper unavailable | Header/errors :723 | Keep | Unchanged. |
| Delivery paused | Header/errors :725 | Keep | Unchanged. |
| Room hub connected | Header/errors :727 | Infrastructure wording | Room host in ordinary UI; hub only in Advanced setup. |
| Connecting | Header/errors :728 | Keep | Unchanged. |
| Resume delivery | Header/errors :733 | Keep | Unchanged. |
| Pause delivery | Header/errors :733 | Keep | Unchanged. |
| Resume delivery | Header/errors :734 | Keep | Unchanged. |
| Pause delivery | Header/errors :734 | Keep | Unchanged. |
| Toggle room context | Header/errors :742 aria-label | Keep | Unchanged. |
| Dismiss error | Header/errors :758 aria-label | Keep | Unchanged. |
| Local helper unavailable. Drafts stay in this window; keep it open and retry when the helper returns. | Header/errors :771 | Keep | Unchanged. |
| Connection unavailable. New messages stay saved on this Mac and sync when the hub returns. | Header/errors :772 | Infrastructure wording | Room host in ordinary UI; hub only in Advanced setup. |
| Opening your room | Setup :782 | Keep | Unchanged. |
| Connecting to the local helper… | Setup :783 | Keep | Unchanged. |
| SETUP | Setup :787 | Capitalization | Sentence case in source; visual uppercase may remain styling. |
| Set up Agent Room | Setup :788 | Keep | Unchanged. |
| Connect existing Codex, Claude Code and OpenCode sessions. Send messages, share plans and request reviews. | Setup :790 | Retired | Remove retired connector copy/option; describe supported connectors only. |
| 01 | Setup :794 | Ambiguous decoration | Remove brand build marker; retain numbered setup steps. |
| Create a room on this Mac | Setup :796 | Overloaded room | Host Agent Room on this Mac |
| Other devices can connect while this Mac is awake. | Setup :797 | Keep | Unchanged. |
| 02 | Setup :801 | Keep | Unchanged. |
| Connect existing sessions | Setup :803 | Naming | Conversation for app conversation; agent for participant. |
| Each agent keeps its own session, tools and permissions. | Setup :805 | Naming | Conversation for app conversation; agent for participant. |
| Create a room | Setup :814 | Overloaded room | Set up this Mac |
| Join an existing room | Setup :820 | Overloaded room | Connect to another Mac |
| SETTINGS | Settings :826 | Capitalization | Sentence case in source; visual uppercase may remain styling. |
| Room settings | Settings :827 | Misleading destination | Settings |
| Appearance | Settings :829 | Keep | Unchanged. |
| Choose a theme. | Settings :830 | Keep | Unchanged. |
| system | Settings :832 | Keep transformed label | Already rendered as System. |
| light | Settings :832 | Keep transformed label | Already rendered as Light. |
| dark | Settings :832 | Keep transformed label | Already rendered as Dark. |
| Devices | Settings :844 | Keep | Unchanged. |
| &#96;${s.name} hosts this room. Keep it awake for other Macs to connect.&#96; | Settings :847 | Keep | Unchanged. |
| This Mac connects outward to the private room hub. | Settings :848 | Infrastructure wording | Room host in ordinary UI; hub only in Advanced setup. |
| This Mac | Settings :857 | Keep | Unchanged. |
| Paired device | Settings :859 | Keep | Unchanged. |
| Access revoked | Settings :860 | Keep | Unchanged. |
| · | Settings :861 | Keep | Unchanged. |
| Room administrator | Settings :863 | Keep | Unchanged. |
| Room member | Settings :864 | Keep | Unchanged. |
| Revoke access | Settings :874 | Keep | Unchanged. |
| Pair another Mac | Settings :888 | Keep | Unchanged. |
| wants to join | Settings :895 | Keep | Unchanged. |
| Device | Settings :896 | Keep | Unchanged. |
| Approve device | Settings :904 | Keep | Unchanged. |
| Background delivery | Settings :910 | Keep | Unchanged. |
| Start Agent Room at login | Settings :926 | Keep | Unchanged. |
| Close the window to keep the room running. Reopen Agent Room from the Dock. Quit Agent Room to stop this device’s helper; saved messages remain on disk. | Settings :930 | Keep | Unchanged. |
| Resume delivery | Settings :940 | Keep | Unchanged. |
| Pause delivery | Settings :940 | Keep | Unchanged. |
| Connections | Settings :944 | Keep | Unchanged. |
| Each binding points to one exact existing conversation. A new session gets a new identity. | Settings :946 | Developer term | Use connection; binding ID only in Advanced setup. |
| Bound room | Settings :961 title | Keep | Unchanged. |
| # | Settings :962 | Keep | Unchanged. |
| Configured for next-turn delivery; check receipts | Settings :967 | Naming | Delivery status for progress; read confirmation for acknowledgement. |
| Configured for on-demand reading | Settings :969 | Keep | Unchanged. |
| Helper bridge active; agent receipt still required | Settings :971 | Developer term | Agent connection; explain delivery limitation. |
| Helper bridge inactive; check host setup | Settings :972 | Developer term | Agent connection; explain delivery limitation. |
| Setup details | Settings :988 | Keep | Unchanged. |
| Remove | Settings :1003 | Keep | Unchanged. |
| Connect a conversation | Settings :1012 | Naming | Connect agent |
| About this build | Settings :1016 | Keep | Unchanged. |
| Reconnect with Keychain | Settings :1022 | Keep | Unchanged. |
| Agent Room 0.1.0 · Local preview release | Settings :1025 | Hardcoded version | Display runtime/package version. |
| Native credentials stay on their own Mac. Device credentials are stored in Keychain. Updates are manual until a signed release service is configured. | Settings :1027 | Keep | Unchanged. |
| Backup saved: | Settings :1035 | Wrong presentation | Backup saved to {path}, in a success notice. |
| Create a consistent backup | Settings :1038 | Implementation wording | Create backup |
| Private hub setup | Settings :1042 | Infrastructure wording | Room host in ordinary UI; hub only in Advanced setup. |
| Expose only the protocol listener through Tailscale Serve HTTPS. Keep the local control listener private. | Settings :1044 | Keep | Unchanged. |
| tailscale serve --bg http://127.0.0.1: | Settings :1048 | Advanced command | Keep exact command syntax in Advanced setup. |
| PLANS & WORK | Plans & work :1056 | Capitalization | Sentence case in source; visual uppercase may remain styling. |
| Shared planning | Plans & work :1057 | Naming | Plans & work |
| Plans, work requests, reviews and decisions for this room. | Plans & work :1059 | Keep | Unchanged. |
| Plan | Plans & work :1070 | Keep | Unchanged. |
| Work request | Plans & work :1080 | Keep | Unchanged. |
| Review | Plans & work :1090 | Keep | Unchanged. |
| Decision | Plans & work :1106 | Keep | Unchanged. |
| No plans or work requests yet. Create one above, or use ⌘K. | Plans & work :1112 | Incomplete/platform-specific | No plans, work requests, reviews or decisions yet. Create one above or use Search. |
| v | Plans & work :1128 | Keep | Unchanged. |
| proposed | Plans & work :1151 | Display capitalization | Capitalize display label; retain wire value. |
| Owner: | Plans & work :1157 | Keep | Unchanged. |
| exact session | Plans & work :1158 | Naming | Connected conversation; preserve exact-identity semantics. |
| Unassigned | Plans & work :1159 | Keep | Unchanged. |
| · evidence: | Plans & work :1160 | Keep | Unchanged. |
| pending | Plans & work :1183 | Display capitalization | Capitalize display label; retain wire value. |
| Revision | Plans & work :1187 | Advanced precision | Version |
| · base | Plans & work :1188 | Keep | Unchanged. |
| · reviewer: | Plans & work :1190 | Keep | Unchanged. |
| exact session | Plans & work :1191 | Naming | Connected conversation; preserve exact-identity semantics. |
| Accepted by | Plans & work :1214 | Keep | Unchanged. |
| Proposed for discussion | Plans & work :1219 | Keep | Unchanged. |
| INBOX | Inbox :1226 | Capitalization | Sentence case in source; visual uppercase may remain styling. |
| Open requests | Inbox :1227 | Too narrow | Inbox |
| Open work and delivery issues. | Inbox :1228 | Keep | Unchanged. |
| Connection requests | Inbox :1232 | Keep | Unchanged. |
| wants to join | Inbox :1242 | Keep | Unchanged. |
| . Approving connects its exact session there; nothing is routed until then. | Inbox :1243 | Naming | Connected conversation; preserve exact-identity semantics. |
| Approve | Inbox :1261 | Keep | Unchanged. |
| Decline | Inbox :1274 | Keep | Unchanged. |
| Needs you | Inbox :1282 | Keep | Unchanged. |
| Queued · bridge not connected | Inbox :1312 | Developer term | Agent connection; explain delivery limitation. |
| Reconnect or resume the exact session to deliver this message | Inbox :1317 | Naming | Connected conversation; preserve exact-identity semantics. |
| Message needs attention | Inbox :1332 | Wrong for failed objects | Save failed / Message failed / Delivery update failed, based on event kind. |
| Nothing needs your attention right now. | Inbox :1341 | Scope ambiguity | No connection requests or delivery issues need attention. |
| Waiting on agents | Inbox :1345 | Keep | Unchanged. |
| &#96;Awaiting ${outstanding.length} agents&#96; | Inbox :1376 | Keep | Unchanged. |
| · | Inbox :1406 | Keep | Unchanged. |
| Your next work request will appear here. | Inbox :1414 | Incomplete empty state | No work requests or messages are waiting on agents. |
| Completed | Inbox :1417 | Keep | Unchanged. |
| Connect agent | Room/composer :1441 | Keep | Unchanged. |
| Conversation | Room/composer :1447 | Keep | Unchanged. |
| Search this room | Room/composer :1458 placeholder | Keep | Unchanged. |
| Search this room | Room/composer :1459 aria-label | Keep | Unchanged. |
| ⌘ K | Room/composer :1461 | Keep | Unchanged. |
| + | Room/composer :1469 | Keep | Unchanged. |
| No messages yet | Room/composer :1471 | Keep | Unchanged. |
| Connect an agent, then send a message. | Room/composer :1472 | Keep | Unchanged. |
| Let’s agree on the objective and the first three steps. | Room/composer :1477 | Keep | Unchanged. |
| Start a plan | Room/composer :1482 | Behavior mismatch | Draft a planning message, or implement plan creation. |
| Request a review | Room/composer :1490 | Behavior mismatch | Fix handler to open review form; retain label. |
| Existing sessions | Room/composer :1496 | Naming | Conversation for app conversation; agent for participant. |
| Explicit receipts | Room/composer :1500 | Naming | Delivery status for progress; read confirmation for acknowledgement. |
| Saved on your Mac | Room/composer :1504 | Keep | Unchanged. |
| No messages match “ | Room/composer :1510 | Keep | Unchanged. |
| ”. | Room/composer :1510 | Keep | Unchanged. |
| ROOM CONVERSATION | Room/composer :1515 | Capitalization | Sentence case in source; visual uppercase may remain styling. |
| Reply | Room/composer :1573 | Keep | Unchanged. |
| ↳ Reply to | Room/composer :1592 | Keep | Unchanged. |
| earlier message | Room/composer :1596 | Keep | Unchanged. |
| To | Room/composer :1605 | Keep | Unchanged. |
| Exact session | Room/composer :1609 | Naming | Connected conversation |
| Room board | Room/composer :1614 | Competing concept | Room — no direct recipient |
| Bridge not connected · message queued until reconnect | Room/composer :1633 | Developer term | Agent connection |
| Queued · bridge not connected | Room/composer :1650 | Developer term | Agent connection; explain delivery limitation. |
| You | Room/composer :1673 | Keep | Unchanged. |
| Cancel unsent message | Room/composer :1687 | Keep | Unchanged. |
| Replying to | Room/composer :1700 | Keep | Unchanged. |
| : | Room/composer :1700 | Keep | Unchanged. |
| Cancel reply | Room/composer :1705 aria-label | Keep | Unchanged. |
| To | Room/composer :1720 | Keep | Unchanged. |
| Message recipient | Room/composer :1722 aria-label | Keep | Unchanged. |
| Room board | Room/composer :1727 | Competing concept | Room — no direct recipient |
| · | Room/composer :1730 | Keep | Unchanged. |
| · | Room/composer :1730 | Keep | Unchanged. |
| Message | Room/composer :1761 aria-label | Keep | Unchanged. |
| Message this agent… | Room/composer :1769 | Keep | Unchanged. |
| Message the room… | Room/composer :1769 | Keep | Unchanged. |
| Routed to this exact conversation | Room/composer :1781 | Keep | Unchanged. |
| Posted to the board · choose an agent to request delivery | Room/composer :1782 | Keep | Unchanged. |
| Send message | Room/composer :1786 aria-label | Keep | Unchanged. |
| Saved locally before sending. Receipts show when an agent has read it. | Room/composer :1796 | Naming | Delivery status / read confirmation, according to state. |
| ↵ to send · ⇧↵ line break | Room/composer :1799 | Keep | Unchanged. |
| In this room | Context :1808 | Keep | Unchanged. |
| Room settings | Context :1811 aria-label | Misleading destination | Settings |
| PARTICIPANTS | Context :1819 | Capitalization | Sentence case in source; visual uppercase may remain styling. |
| Connect an agent’s existing conversation to get started. | Context :1823 | Keep | Unchanged. |
| Next-turn delivery | Context :1843 | Qualification needed | Queued for the agent’s next turn |
| Read on demand | Context :1845 | Mode not app identity | On-demand agent; show app/model separately when known. |
| On another Mac · check receipts | Context :1847 | Naming | Delivery status for progress; read confirmation for acknowledgement. |
| Helper bridge active · check receipts | Context :1850 | Developer term | Agent connection; explain delivery limitation. |
| Helper bridge inactive · check setup | Context :1851 | Developer term | Agent connection; explain delivery limitation. |
| Connect a conversation | Context :1862 | Naming | Connect agent |
| CURRENT PLAN | Context :1867 | Capitalization | Sentence case in source; visual uppercase may remain styling. |
| Add plan | Context :1870 aria-label | Keep | Unchanged. |
| Version | Context :1902 | Keep | Unchanged. |
| No plan yet. | Context :1906 | Keep | Unchanged. |
| WORK & REVIEWS | Context :1911 | Capitalization | Sentence case in source; visual uppercase may remain styling. |
| Add work request | Context :1914 aria-label | Keep | Unchanged. |
| Revision | Context :1938 | Advanced precision | Version |
| · Self-review | Context :1939 | Keep | Unchanged. |
| No work requests or reviews. | Context :1947 | Keep | Unchanged. |
| DECISIONS | Context :1952 | Capitalization | Sentence case in source; visual uppercase may remain styling. |
| Add decision | Context :1955 aria-label | Keep | Unchanged. |
| Accepted by | Context :1985 | Keep | Unchanged. |
| Proposed for discussion | Context :1990 | Keep | Unchanged. |
| No decisions recorded. | Context :1995 | Keep | Unchanged. |
| Messages use exact session IDs. | Context :2000 | Naming | Connected conversation; preserve exact-identity semantics. |
| Create room | Dialogs/palette dispatch :2007 title | Context dependent | Set up this Mac in onboarding; Create room in room naming form. |
| This Mac will host the room. You can pair more Macs once it’s ready. | Dialogs/palette dispatch :2012 | Keep | Unchanged. |
| Device name | Dialogs/palette dispatch :2016 | Keep | Unchanged. |
| My Mac | Dialogs/palette dispatch :2021 placeholder | Keep | Unchanged. |
| Create room | Dialogs/palette dispatch :2026 | Context dependent | Set up this Mac in onboarding; Create room in room naming form. |
| Join an existing room | Dialogs/palette dispatch :2032 title | Overloaded room | Connect to another Mac |
| Create a pairing invitation on the Mac that hosts your room. Use its private HTTPS address. | Dialogs/palette dispatch :2048 | Keep | Unchanged. |
| This device’s name | Dialogs/palette dispatch :2052 | Keep | Unchanged. |
| My other Mac | Dialogs/palette dispatch :2053 placeholder | Keep | Unchanged. |
| Private hub address | Dialogs/palette dispatch :2056 | Infrastructure wording | Room host in ordinary UI; hub only in Advanced setup. |
| https://your-mac.your-tailnet.ts.net | Dialogs/palette dispatch :2061 placeholder | Keep | Unchanged. |
| Invitation ID | Dialogs/palette dispatch :2065 | Keep | Unchanged. |
| Pairing proof | Dialogs/palette dispatch :2069 | Keep | Unchanged. |
| Request to join | Dialogs/palette dispatch :2073 | Keep | Unchanged. |
| I’ve approved this Mac — finish pairing | Dialogs/palette dispatch :2080 | Keep | Unchanged. |
| Pair another Mac | Dialogs/palette dispatch :2086 title | Keep | Unchanged. |
| Open Agent Room on your other Mac and choose | Dialogs/palette dispatch :2088 | Keep | Unchanged. |
| Join an existing room | Dialogs/palette dispatch :2089 | Overloaded room | Connect to another Mac |
| . This invitation expires in five minutes. | Dialogs/palette dispatch :2089 | Keep | Unchanged. |
| Invitation ID | Dialogs/palette dispatch :2093 | Keep | Unchanged. |
| Single-use proof | Dialogs/palette dispatch :2097 | Keep | Unchanged. |
| Copy these directly into the other app. Then approve the device in Settings on this Mac. The invitation grants access only to General. | Dialogs/palette dispatch :2107 | Keep | Unchanged. |
| View pairing requests | Dialogs/palette dispatch :2117 | Keep | Unchanged. |
| Name this room | Dialogs/palette dispatch :2122 title | Keep | Unchanged. |
| Room name | Dialogs/palette dispatch :2133 | Keep | Unchanged. |
| Room name | Dialogs/palette dispatch :2138 placeholder | Keep | Unchanged. |
| Create room | Dialogs/palette dispatch :2143 | Context dependent | Set up this Mac in onboarding; Create room in room naming form. |
| Connect an existing conversation | Dialogs/palette dispatch :2150 title | Naming | Connect agent — choose an existing conversation |
| Choose a conversation on | Dialogs/palette dispatch :2173 | Keep | Unchanged. |
| . Its native identity stays unchanged. | Dialogs/palette dispatch :2173 | Developer term | Use conversation ID in the agent app; retain native keys in Advanced setup. |
| Agent app | Dialogs/palette dispatch :2177 | Keep | Unchanged. |
| Codex | Dialogs/palette dispatch :2179 | Keep | Unchanged. |
| OpenCode | Dialogs/palette dispatch :2180 | Retired | Remove retired connector copy/option; describe supported connectors only. |
| Claude Code | Dialogs/palette dispatch :2181 | Keep | Unchanged. |
| Claude app · read on demand | Dialogs/palette dispatch :2182 | Keep | Unchanged. |
| MCP (any agent) · read on demand | Dialogs/palette dispatch :2183 | Advanced precision | Keep protocol name in connector picker/setup; explain using the agent app’s tools. |
| Conversation title | Dialogs/palette dispatch :2187 | Naming | Agent name in this room |
| Implementation review | Dialogs/palette dispatch :2191 placeholder | Keep | Unchanged. |
| Exact native session ID | Dialogs/palette dispatch :2196 | Developer term | Use conversation ID in the agent app; retain native keys in Advanced setup. |
| Task UUID or ses_… | Dialogs/palette dispatch :2200 placeholder | Keep | Unchanged. |
| Local directory · required for OpenCode | Dialogs/palette dispatch :2205 | Retired | Remove retired connector copy/option; describe supported connectors only. |
| /absolute/path/to/workspace | Dialogs/palette dispatch :2208 placeholder | Keep | Unchanged. |
| Model · optional | Dialogs/palette dispatch :2212 | Keep | Unchanged. |
| e.g. claude-opus-4-8 | Dialogs/palette dispatch :2215 placeholder | Hardcoded example | Model name (optional), no unverified model example. |
| Codex can receive on its next turn. OpenCode needs the local plugin. Claude app sessions can read messages using ordinary MCP tools during a turn; channel push needs separate host support. Any other MCP client can connect generically, self-identifying its own session. Registration alone doesn’t prove receipt. | Dialogs/palette dispatch :2220 | Retired | Remove retired connector copy/option; describe supported connectors only. |
| Connect conversation | Dialogs/palette dispatch :2227 | Naming | Connect agent |
| Conversation setup | Dialogs/palette dispatch :2234 | Keep | Unchanged. |
| Delivery uses the installed Codex queue for this exact task. Replies and receipts need the separate desktop room tools below. | Dialogs/palette dispatch :2243 | Naming | Delivery status for progress; read confirmation for acknowledgement. |
| Copy the bundled OpenCode plugin into your OpenCode plugins folder, then restart OpenCode when its sessions are idle. The plugin finds this exact conversation automatically. | Dialogs/palette dispatch :2245 | Retired | Remove retired connector copy/option; describe supported connectors only. |
| Claude app read-on-demand uses ordinary MCP tools in this existing conversation. For optional background watch, the agent can call room_monitor_setup and start its returned command with the native app Monitor tool under normal host permissions. Each watch expires after at most 30 minutes and must be renewed; real idle delivery needs a receiving read and acknowledgement. | Dialogs/palette dispatch :2247 | Developer term | Use conversation ID in the agent app; retain native keys in Advanced setup. |
| Generic MCP read-on-demand uses ordinary MCP tools in this existing conversation. The connecting client self-identifies its own native session; no push and no idle-wake, the agent reads when it is active. | Dialogs/palette dispatch :2249 | Developer term | Use conversation ID in the agent app; retain native keys in Advanced setup. |
| Connect the bundled MCP helper to this same native conversation. Claude Code channels require host support and a launch opt-in. Custom channels in research preview require the development allowlist flag; check whether this Desktop host can supply it. | Dialogs/palette dispatch :2250 | Developer term | Use conversation ID in the agent app; retain native keys in Advanced setup. |
| Native conversation | Dialogs/palette dispatch :2253 | Keep | Unchanged. |
| Desktop room binding | Dialogs/palette dispatch :2257 | Developer term | Use connection; binding ID only in Advanced setup. |
| Plugin files are inside Agent Room.app at Contents/Resources/adapters. Copy agent-room-desktop.ts and the agent-room-desktop folder together into ~/.config/opencode/plugins. No password or binding file is needed. | Dialogs/palette dispatch :2262 | Developer term | Use connection; binding ID only in Advanced setup. |
| Use the bundled agent-room-helper with | Dialogs/palette dispatch :2268 | Keep | Unchanged. |
| --mcp | Dialogs/palette dispatch :2268 | Advanced command | Keep exact command syntax in Advanced setup. |
| and --claude-channel | Dialogs/palette dispatch :2270 | Keep | Unchanged. |
| and --claude-app | Dialogs/palette dispatch :2272 | Keep | Unchanged. |
| and --generic (set AGENT_ROOM_NATIVE, and optionally AGENT_ROOM_MODEL) | Dialogs/palette dispatch :2274 | Keep | Unchanged. |
| . Replace the old Agent Room MCP command. The host supplies this conversation’s identity; never put a shared session ID in global configuration. Reload the MCP connection when the session is ready. | Dialogs/palette dispatch :2275 | Naming | Conversation for app conversation; agent for participant. |
| For the Claude Code CLI research preview, launch with | Dialogs/palette dispatch :2283 | Keep | Unchanged. |
| --dangerously-load-development-channels server:agent-room | Dialogs/palette dispatch :2284 | Advanced command | Keep exact command syntax in Advanced setup. |
| . This opts in the custom channel only. If the Desktop Code host cannot provide an equivalent launch opt-in and native session identity, push delivery remains unsupported there. A loaded MCP tool list or active helper process does not establish receipt. | Dialogs/palette dispatch :2285 | Developer term | Use conversation ID in the agent app; retain native keys in Advanced setup. |
| A receipt means the receiving agent explicitly confirmed reading. “Submitted” only means its app accepted the prompt. | Dialogs/palette dispatch :2292 | Naming | Delivery status for progress; read confirmation for acknowledgement. |
| Done | Dialogs/palette dispatch :2296 | Keep | Unchanged. |
| Remove connection | Dialogs/palette dispatch :2301 title | Keep | Unchanged. |
| Remove the connection to “ | Dialogs/palette dispatch :2303 | Keep | Unchanged. |
| ”? The session is disconnected; reconnecting later creates a new one. | Dialogs/palette dispatch :2303 | False identity claim | ”? This disconnects the conversation. Reconnecting it restores its identity. |
| Remove connection | Dialogs/palette dispatch :2311 | Keep | Unchanged. |
| Cancel | Dialogs/palette dispatch :2318 | Keep | Unchanged. |
| Save cancelled. Review your changes and try again. | Workflow :2445 | Keep | Unchanged. |
| Saved on this Mac, awaiting hub confirmation. Check again before submitting another change. | Workflow :2449 | Infrastructure wording | Room host in ordinary UI; hub only in Advanced setup. |
| Update | Workflow :2456 | Keep | Unchanged. |
| New request | Workflow :2456 | Wrong noun | New plan / New work request / New review / New decision |
| Type | Workflow :2501 | Keep | Unchanged. |
| Work request | Workflow :2507 | Keep | Unchanged. |
| Shared plan | Workflow :2508 | Naming | Plan |
| Decision | Workflow :2509 | Keep | Unchanged. |
| Review packet | Workflow :2510 | Naming | Review |
| Objective | Workflow :2516 | Keep | Unchanged. |
| What are we trying to achieve? | Workflow :2521 placeholder | Keep | Unchanged. |
| Next steps · one per line | Workflow :2525 | Keep | Unchanged. |
| Decision | Workflow :2537 | Keep | Unchanged. |
| Status | Workflow :2541 | Keep | Unchanged. |
| proposed | Workflow :2543 | Display capitalization | Capitalize display label; retain wire value. |
| accepted | Workflow :2543 | Display capitalization | Capitalize display label; retain wire value. |
| superseded | Workflow :2543 | Display capitalization | Capitalize display label; retain wire value. |
| Accepting records you as the decision maker. It doesn’t grant new tool permissions. | Workflow :2549 | Keep | Unchanged. |
| Request | Workflow :2558 | Keep | Unchanged. |
| Review the delivery recovery behavior | Workflow :2563 placeholder | Keep | Unchanged. |
| Scope and acceptance | Workflow :2567 | Keep | Unchanged. |
| Artifact | Workflow :2574 | Developer term | Item to review |
| Repository / artifact reference | Workflow :2579 placeholder | Developer term | Item to review |
| Exact revision | Workflow :2584 | Advanced precision | Version / exact revision; preserve hashes. |
| Commit or content digest | Workflow :2589 placeholder | Keep | Unchanged. |
| Base revision | Workflow :2593 | Advanced precision | Version / exact revision; preserve hashes. |
| Checks and test evidence | Workflow :2598 | Keep | Unchanged. |
| Only the exact reviewer can issue a verdict through their room tools. Changing the artifact resets approval. | Workflow :2602 | Incomplete behavior claim | Only the assigned reviewer can approve through their agent tools. Saving here resets verdict and findings (until fixed). |
| Reviewer | Workflow :2608 | Keep | Unchanged. |
| Owner | Workflow :2608 | Keep | Unchanged. |
| Choose an exact conversation | Workflow :2615 | Keep | Unchanged. |
| · | Workflow :2619 | Keep | Unchanged. |
| Status | Workflow :2627 | Keep | Unchanged. |
| proposed | Workflow :2630 | Display capitalization | Capitalize display label; retain wire value. |
| accepted | Workflow :2631 | Display capitalization | Capitalize display label; retain wire value. |
| working | Workflow :2632 | Display capitalization | Capitalize display label; retain wire value. |
| blocked | Workflow :2633 | Display capitalization | Capitalize display label; retain wire value. |
| ready for review | Workflow :2634 | Display capitalization | Capitalize display label; retain wire value. |
| resolved | Workflow :2635 | Display capitalization | Capitalize display label; retain wire value. |
| cancelled | Workflow :2636 | Display capitalization | Capitalize display label; retain wire value. |
| Completion evidence | Workflow :2643 | Keep | Unchanged. |
| Confirming save… | Workflow :2656 | Keep | Unchanged. |
| Check save status | Workflow :2656 | Keep | Unchanged. |
| Save | Workflow :2656 | Keep | Unchanged. |

## Excluded candidate ledger

Imports, protocol/action IDs, selectors, CSS classes, form keys, attributes or control-flow comparisons, not additional displayed copy at these locations. Data values are covered separately.

| Line | Candidate | AST context |
|---|---|---|
| 1 | react | ImportDeclaration |
| 2 | react-dom/client | ImportDeclaration |
| 3 | @tauri-apps/api/core | ImportDeclaration |
| 29 | lucide-react | ImportDeclaration |
| 30 | ./styles.css | ImportDeclaration |
| 105 | general | PropertyAssignment |
| 106 | general | PropertyAssignment |
| 107 | general | PropertyAssignment |
| 125 | general | BinaryExpression |
| 128 | pull | ArrayLiteralExpression |
| 128 | mcp | ArrayLiteralExpression |
| 131 | codex-queue | PropertyAssignment |
| 132 | opencode-bridge | PropertyAssignment |
| 133 | claude-channel | PropertyAssignment |
| 146 | idle | BinaryExpression |
| 147 | good | LiteralType |
| 147 | warn | LiteralType |
| 147 | down | LiteralType |
| 154 | good | PropertyAssignment |
| 158 | down | PropertyAssignment |
| 161 | warn | PropertyAssignment |
| 166 | warn | PropertyAssignment |
| 169 | codex-queue | BinaryExpression |
| 171 | good | PropertyAssignment |
| 176 | down | PropertyAssignment |
| 179 | good | PropertyAssignment |
| 182 | unavailable | BinaryExpression |
| 196 | control | CallExpression |
| 197 | /control | CallExpression |
| 198 | POST | PropertyAssignment |
| 199 | Content-Type | PropertyAssignment |
| 199 | application/json | PropertyAssignment |
| 236 | goto-room | PropertyAssignment |
| 237 | goto-inbox | PropertyAssignment |
| 238 | goto-objects | PropertyAssignment |
| 239 | goto-settings | PropertyAssignment |
| 240 | new-message | PropertyAssignment |
| 241 | new-work | PropertyAssignment |
| 242 | new-plan | PropertyAssignment |
| 243 | new-review | PropertyAssignment |
| 244 | new-decision | PropertyAssignment |
| 245 | connect | PropertyAssignment |
| 249 | message | BinaryExpression |
| 255 | msg- | BinaryExpression |
| 265 | session- | BinaryExpression |
| 276 | object- | BinaryExpression |
| 290 | palette | JsxAttribute / className |
| 296 | palette-input | JsxAttribute / className |
| 305 | ArrowDown | BinaryExpression |
| 308 | ArrowUp | BinaryExpression |
| 311 | Enter | BinaryExpression |
| 314 | Escape | BinaryExpression |
| 321 | palette-list | JsxAttribute / className |
| 327 | palette-group | JsxAttribute / className |
| 330 | palette-item | BinaryExpression |
| 330 | active | ConditionalExpression |
| 341 | palette-empty | JsxAttribute / className |
| 361 | identity-chip status- | BinaryExpression |
| 361 | idle | BinaryExpression |
| 362 | identity-dot | JsxAttribute / className |
| 363 | identity-text | JsxAttribute / className |
| 392 | dialog-head | JsxAttribute / className |
| 394 | icon | JsxAttribute / className |
| 407 | room | CallExpression |
| 421 | appearance | CallExpression |
| 421 | system | BinaryExpression |
| 423 | system | ReturnStatement |
| 433 | snapshot | CallExpression |
| 446 | runtime_info | CallExpression |
| 451 | k | BinaryExpression |
| 455 | Escape | BinaryExpression |
| 460 | keydown | CallExpression |
| 461 | keydown | CallExpression |
| 464 | system | BinaryExpression |
| 465 | data-theme | CallExpression |
| 467 | data-theme | CallExpression |
| 470 | appearance | CallExpression |
| 477 | instant | PropertyAssignment |
| 508 | acknowledged | BinaryExpression |
| 511 | work | BinaryExpression |
| 512 | resolved | BinaryExpression |
| 513 | cancelled | BinaryExpression |
| 522 | unavailable | ArrayLiteralExpression |
| 522 | uncertain | ArrayLiteralExpression |
| 523 | pending | BinaryExpression |
| 526 | pull | ArrayLiteralExpression |
| 526 | mcp | ArrayLiteralExpression |
| 526 | codex-queue | ArrayLiteralExpression |
| 533 | failed | BinaryExpression |
| 536 | message | BinaryExpression |
| 542 | waiting | ArrayLiteralExpression |
| 542 | pending | ArrayLiteralExpression |
| 542 | submitted | ArrayLiteralExpression |
| 547 | message | BinaryExpression |
| 549 | &#96;${e.body.text} ${author(e)}&#96; | PropertyAccessExpression |
| 557 | send | CallExpression |
| 581 | shell | JsxAttribute / className |
| 582 | sidebar | JsxAttribute / className |
| 583 | brand | JsxAttribute / className |
| 584 | brand-mark | JsxAttribute / className |
| 588 | version | JsxAttribute / className |
| 591 | nav | BinaryExpression |
| 591 | inbox | BinaryExpression |
| 591 | selected | ConditionalExpression |
| 592 | inbox | CallExpression |
| 597 | count | JsxAttribute / className |
| 603 | nav | BinaryExpression |
| 603 | objects | BinaryExpression |
| 603 | selected | ConditionalExpression |
| 604 | objects | CallExpression |
| 609 | count | JsxAttribute / className |
| 613 | nav | JsxAttribute / className |
| 619 | shortcut | JsxAttribute / className |
| 623 | nav-label | JsxAttribute / className |
| 625 | nav pinned-view | JsxAttribute / className |
| 627 | inbox | CallExpression |
| 634 | count | JsxAttribute / className |
| 638 | nav pinned-view static | JsxAttribute / className |
| 644 | count | JsxAttribute / className |
| 649 | nav-label | JsxAttribute / className |
| 654 | nav | BinaryExpression |
| 655 | room | BinaryExpression |
| 655 | selected | ConditionalExpression |
| 658 | room-select | CallExpression |
| 659 | room | CallExpression |
| 667 | status-dot status- | BinaryExpression |
| 667 | idle | BinaryExpression |
| 671 | count | JsxAttribute / className |
| 673 | room-dot | JsxAttribute / className |
| 676 | nav | JsxAttribute / className |
| 676 | new-room | CallExpression |
| 680 | sidebar-note | JsxAttribute / className |
| 681 | tiny-rule | JsxAttribute / className |
| 688 | sidebar-bottom | JsxAttribute / className |
| 690 | nav | BinaryExpression |
| 690 | settings | BinaryExpression |
| 690 | selected | ConditionalExpression |
| 691 | settings | CallExpression |
| 696 | device-label | JsxAttribute / className |
| 699 | connection-dot | BinaryExpression |
| 699 | online | ConditionalExpression |
| 703 | workspace | JsxAttribute / className |
| 704 | topbar | JsxAttribute / className |
| 705 | breadcrumb | JsxAttribute / className |
| 708 | room | BinaryExpression |
| 710 | inbox | BinaryExpression |
| 712 | objects | BinaryExpression |
| 717 | header-actions | JsxAttribute / className |
| 718 | quiet-status | JsxAttribute / className |
| 720 | connection-dot | BinaryExpression |
| 720 | online | ConditionalExpression |
| 732 | icon | JsxAttribute / className |
| 735 | pause | CallExpression |
| 741 | icon | JsxAttribute / className |
| 754 | error-banner | JsxAttribute / className |
| 754 | alert | JsxAttribute / role |
| 757 | icon | JsxAttribute / className |
| 769 | notice | JsxAttribute / className |
| 775 | main-row | JsxAttribute / className |
| 778 | empty-state | JsxAttribute / className |
| 779 | brand-mark | JsxAttribute / className |
| 786 | onboarding | JsxAttribute / className |
| 787 | eyebrow | JsxAttribute / className |
| 793 | onboard-line | JsxAttribute / className |
| 800 | onboard-line | JsxAttribute / className |
| 809 | onboard-actions | JsxAttribute / className |
| 811 | primary | JsxAttribute / className |
| 812 | create | CallExpression |
| 817 | secondary | JsxAttribute / className |
| 818 | join | CallExpression |
| 824 | settings | BinaryExpression |
| 825 | settings-page | JsxAttribute / className |
| 826 | eyebrow | JsxAttribute / className |
| 831 | segmented | JsxAttribute / className |
| 835 | active | ConditionalExpression |
| 846 | host | BinaryExpression |
| 851 | settings-row | JsxAttribute / className |
| 862 | admin | BinaryExpression |
| 867 | host | BinaryExpression |
| 869 | text-button | JsxAttribute / className |
| 871 | revoke | CallExpression |
| 879 | host | BinaryExpression |
| 881 | secondary | JsxAttribute / className |
| 883 | pair-create | CallExpression |
| 884 | pair | CallExpression |
| 892 | pair-request | JsxAttribute / className |
| 899 | primary | JsxAttribute / className |
| 901 | pair-approve | CallExpression |
| 912 | checkbox-label | JsxAttribute / className |
| 914 | checkbox | JsxAttribute / type |
| 917 | set_login_start | CallExpression |
| 935 | secondary | JsxAttribute / className |
| 937 | pause | CallExpression |
| 950 | settings-row | JsxAttribute / className |
| 954 | binding-meta | JsxAttribute / className |
| 960 | mono | JsxAttribute / className |
| 966 | codex-queue | BinaryExpression |
| 976 | text-button | JsxAttribute / className |
| 980 | connection | PropertyAssignment |
| 985 | connection | CallExpression |
| 991 | text-button | JsxAttribute / className |
| 995 | connection | PropertyAssignment |
| 1000 | remove-connection | CallExpression |
| 1008 | secondary | JsxAttribute / className |
| 1009 | connect | CallExpression |
| 1019 | secondary | JsxAttribute / className |
| 1020 | unlock | CallExpression |
| 1032 | secondary | JsxAttribute / className |
| 1034 | backup | CallExpression |
| 1054 | objects | BinaryExpression |
| 1055 | objects-page | JsxAttribute / className |
| 1056 | eyebrow | JsxAttribute / className |
| 1058 | lead | JsxAttribute / className |
| 1061 | objects-actions | JsxAttribute / className |
| 1063 | secondary | JsxAttribute / className |
| 1066 | workflow:plan | CallExpression |
| 1073 | secondary | JsxAttribute / className |
| 1076 | workflow:work | CallExpression |
| 1083 | secondary | JsxAttribute / className |
| 1086 | workflow:review | CallExpression |
| 1093 | secondary | JsxAttribute / className |
| 1097 | decision | PropertyAssignment |
| 1102 | workflow:decision | CallExpression |
| 1110 | quiet-empty | JsxAttribute / className |
| 1116 | plan | BinaryExpression |
| 1119 | object-card | JsxAttribute / className |
| 1123 | workflow:plan | CallExpression |
| 1126 | object-card-head | JsxAttribute / className |
| 1128 | count | JsxAttribute / className |
| 1138 | work | BinaryExpression |
| 1141 | object-card state- | BinaryExpression |
| 1141 | proposed | BinaryExpression |
| 1145 | workflow:work | CallExpression |
| 1148 | object-card-head | JsxAttribute / className |
| 1150 | object-state | JsxAttribute / className |
| 1165 | review | BinaryExpression |
| 1168 | object-card | JsxAttribute / className |
| 1172 | workflow:review | CallExpression |
| 1175 | object-card-head | JsxAttribute / className |
| 1179 | object-state | BinaryExpression |
| 1180 | approved | BinaryExpression |
| 1180 | ok | ConditionalExpression |
| 1198 | decision | BinaryExpression |
| 1201 | object-card | JsxAttribute / className |
| 1205 | workflow:decision | CallExpression |
| 1208 | object-card-head | JsxAttribute / className |
| 1210 | object-state | JsxAttribute / className |
| 1224 | inbox | BinaryExpression |
| 1225 | inbox-page | JsxAttribute / className |
| 1226 | eyebrow | JsxAttribute / className |
| 1228 | lead | JsxAttribute / className |
| 1230 | request-list | JsxAttribute / className |
| 1233 | count | JsxAttribute / className |
| 1236 | inbox-item request | JsxAttribute / className |
| 1247 | mono | JsxAttribute / className |
| 1249 | request-actions | JsxAttribute / className |
| 1251 | primary | JsxAttribute / className |
| 1254 | request-decide | CallExpression |
| 1264 | secondary | JsxAttribute / className |
| 1267 | request-decide | CallExpression |
| 1282 | count | JsxAttribute / className |
| 1290 | pending | BinaryExpression |
| 1293 | pull | ArrayLiteralExpression |
| 1293 | mcp | ArrayLiteralExpression |
| 1293 | codex-queue | ArrayLiteralExpression |
| 1297 | inbox-item | JsxAttribute / className |
| 1300 | room | CallExpression |
| 1327 | failed | BinaryExpression |
| 1329 | inbox-item | JsxAttribute / className |
| 1339 | quiet-empty | JsxAttribute / className |
| 1346 | count | JsxAttribute / className |
| 1354 | waiting | ArrayLiteralExpression |
| 1354 | pending | ArrayLiteralExpression |
| 1354 | submitted | ArrayLiteralExpression |
| 1358 | inbox-item | JsxAttribute / className |
| 1359 | unacked- | BinaryExpression |
| 1361 | room | CallExpression |
| 1366 | message- | BinaryExpression |
| 1367 | center | PropertyAssignment |
| 1386 | , | CallExpression |
| 1395 | inbox-item | JsxAttribute / className |
| 1399 | workflow | CallExpression |
| 1413 | quiet-empty | JsxAttribute / className |
| 1420 | work | BinaryExpression |
| 1420 | resolved | BinaryExpression |
| 1423 | inbox-item | JsxAttribute / className |
| 1434 | room-heading | JsxAttribute / className |
| 1437 | secondary | JsxAttribute / className |
| 1438 | connect | CallExpression |
| 1444 | conversation-toolbar | JsxAttribute / className |
| 1448 | count | JsxAttribute / className |
| 1449 | message | BinaryExpression |
| 1452 | search-field | JsxAttribute / className |
| 1464 | conversation | JsxAttribute / className |
| 1464 | polite | JsxAttribute / aria-live |
| 1466 | room-welcome | JsxAttribute / className |
| 1467 | welcome-symbol | JsxAttribute / className |
| 1473 | suggestions | JsxAttribute / className |
| 1487 | workflow | CallExpression |
| 1493 | room-principles | JsxAttribute / className |
| 1509 | quiet-empty | JsxAttribute / className |
| 1514 | day-divider | JsxAttribute / className |
| 1524 | message | JsxAttribute / className |
| 1525 | message- | BinaryExpression |
| 1530 | avatar | BinaryExpression |
| 1530 | human | ConditionalExpression |
| 1539 | message-main | JsxAttribute / className |
| 1540 | message-meta | JsxAttribute / className |
| 1561 | 2-digit | PropertyAssignment |
| 1562 | 2-digit | PropertyAssignment |
| 1566 | message-reply | JsxAttribute / className |
| 1578 | reply-source | JsxAttribute / className |
| 1585 | message- | BinaryExpression |
| 1587 | center | PropertyAssignment |
| 1599 | message-text | JsxAttribute / className |
| 1602 | message-foot | JsxAttribute / className |
| 1611 | , | CallExpression |
| 1622 | pending | BinaryExpression |
| 1625 | pull | ArrayLiteralExpression |
| 1625 | mcp | ArrayLiteralExpression |
| 1625 | codex-queue | ArrayLiteralExpression |
| 1637 | receipt | BinaryExpression |
| 1638 | stuck | ConditionalExpression |
| 1642 | acknowledged | BinaryExpression |
| 1644 | submitted | BinaryExpression |
| 1665 | message | BinaryExpression |
| 1669 | message unsynced | JsxAttribute / className |
| 1670 | avatar human | JsxAttribute / className |
| 1671 | message-main | JsxAttribute / className |
| 1672 | message-meta | JsxAttribute / className |
| 1675 | message-text | JsxAttribute / className |
| 1678 | message-foot | JsxAttribute / className |
| 1680 | saved | BinaryExpression |
| 1682 | text-button | JsxAttribute / className |
| 1684 | cancel | CallExpression |
| 1696 | composer-area | JsxAttribute / className |
| 1698 | replying | JsxAttribute / className |
| 1704 | icon | JsxAttribute / className |
| 1713 | composer | JsxAttribute / className |
| 1719 | composer-target | JsxAttribute / className |
| 1736 | good | BinaryExpression |
| 1739 | target-health | BinaryExpression |
| 1772 | Enter | BinaryExpression |
| 1778 | composer-bottom | JsxAttribute / className |
| 1785 | submit | JsxAttribute / type |
| 1787 | send | JsxAttribute / className |
| 1794 | composer-help | JsxAttribute / className |
| 1805 | room | BinaryExpression |
| 1806 | context | JsxAttribute / className |
| 1807 | context-title | JsxAttribute / className |
| 1810 | icon | JsxAttribute / className |
| 1812 | settings | CallExpression |
| 1818 | section-label | JsxAttribute / className |
| 1822 | context-empty | JsxAttribute / className |
| 1827 | participant | JsxAttribute / className |
| 1828 | avatar | JsxAttribute / className |
| 1841 | participant-status | JsxAttribute / className |
| 1842 | codex-queue | BinaryExpression |
| 1858 | text-button | JsxAttribute / className |
| 1859 | connect | CallExpression |
| 1866 | section-label | JsxAttribute / className |
| 1869 | icon | JsxAttribute / className |
| 1874 | plan | PropertyAssignment |
| 1879 | workflow | CallExpression |
| 1886 | plan | BinaryExpression |
| 1890 | object-block | JsxAttribute / className |
| 1893 | workflow | CallExpression |
| 1905 | plan | BinaryExpression |
| 1906 | context-empty | JsxAttribute / className |
| 1910 | section-label | JsxAttribute / className |
| 1913 | icon | JsxAttribute / className |
| 1917 | workflow | CallExpression |
| 1924 | work | ArrayLiteralExpression |
| 1924 | review | ArrayLiteralExpression |
| 1927 | object-block | JsxAttribute / className |
| 1931 | workflow | CallExpression |
| 1936 | review | BinaryExpression |
| 1945 | work | ArrayLiteralExpression |
| 1945 | review | ArrayLiteralExpression |
| 1947 | context-empty | JsxAttribute / className |
| 1951 | section-label | JsxAttribute / className |
| 1954 | icon | JsxAttribute / className |
| 1959 | decision | PropertyAssignment |
| 1964 | workflow | CallExpression |
| 1971 | decision | BinaryExpression |
| 1974 | object-block | JsxAttribute / className |
| 1978 | workflow | CallExpression |
| 1994 | decision | BinaryExpression |
| 1995 | context-empty | JsxAttribute / className |
| 1998 | context-footer | JsxAttribute / className |
| 2006 | create | BinaryExpression |
| 2009 | create | CallExpression |
| 2009 | name | CallExpression |
| 2018 | name | JsxAttribute / name |
| 2025 | primary wide | JsxAttribute / className |
| 2031 | join | BinaryExpression |
| 2036 | join-request | CallExpression |
| 2038 | url | CallExpression |
| 2039 | id | CallExpression |
| 2040 | proof | CallExpression |
| 2041 | name | CallExpression |
| 2053 | name | JsxAttribute / name |
| 2058 | url | JsxAttribute / name |
| 2059 | url | JsxAttribute / type |
| 2066 | id | JsxAttribute / name |
| 2070 | proof | JsxAttribute / name |
| 2070 | password | JsxAttribute / type |
| 2070 | off | JsxAttribute / autoComplete |
| 2072 | primary wide | JsxAttribute / className |
| 2076 | button | JsxAttribute / type |
| 2077 | secondary wide | JsxAttribute / className |
| 2078 | join-finish | CallExpression |
| 2085 | pair | BinaryExpression |
| 2094 | mono | JsxAttribute / className |
| 2099 | mono | JsxAttribute / className |
| 2101 | password | JsxAttribute / type |
| 2106 | small | JsxAttribute / className |
| 2111 | primary wide | JsxAttribute / className |
| 2114 | settings | CallExpression |
| 2121 | new-room | BinaryExpression |
| 2125 | title | CallExpression |
| 2127 | room-create | CallExpression |
| 2128 | room | CallExpression |
| 2135 | title | JsxAttribute / name |
| 2142 | primary wide | JsxAttribute / className |
| 2148 | connect | BinaryExpression |
| 2155 | bind | CallExpression |
| 2156 | app | CallExpression |
| 2157 | title | CallExpression |
| 2158 | native | CallExpression |
| 2159 | directory | CallExpression |
| 2160 | model | CallExpression |
| 2164 | connection | PropertyAssignment |
| 2169 | connection | CallExpression |
| 2178 | app | JsxAttribute / name |
| 2179 | codex-queue | JsxAttribute / value |
| 2180 | opencode-bridge | JsxAttribute / value |
| 2181 | claude-channel | JsxAttribute / value |
| 2182 | pull | JsxAttribute / value |
| 2183 | mcp | JsxAttribute / value |
| 2189 | title | JsxAttribute / name |
| 2198 | native | JsxAttribute / name |
| 2207 | directory | JsxAttribute / name |
| 2214 | model | JsxAttribute / name |
| 2219 | small | JsxAttribute / className |
| 2226 | primary wide | JsxAttribute / className |
| 2232 | connection | BinaryExpression |
| 2237 | setup-kind | JsxAttribute / className |
| 2242 | codex-queue | BinaryExpression |
| 2244 | opencode-bridge | BinaryExpression |
| 2246 | pull | BinaryExpression |
| 2248 | mcp | BinaryExpression |
| 2254 | mono | JsxAttribute / className |
| 2258 | mono | JsxAttribute / className |
| 2260 | opencode-bridge | BinaryExpression |
| 2261 | small | JsxAttribute / className |
| 2267 | small | JsxAttribute / className |
| 2269 | claude-channel | BinaryExpression |
| 2271 | pull | BinaryExpression |
| 2273 | mcp | BinaryExpression |
| 2281 | claude-channel | BinaryExpression |
| 2282 | small | JsxAttribute / className |
| 2291 | small | JsxAttribute / className |
| 2295 | primary wide | JsxAttribute / className |
| 2300 | remove-connection | BinaryExpression |
| 2307 | primary wide | JsxAttribute / className |
| 2309 | binding-remove | CallExpression |
| 2314 | button | JsxAttribute / type |
| 2315 | secondary wide | JsxAttribute / className |
| 2322 | workflow | CallExpression |
| 2325 | : | CallExpression |
| 2329 | object | CallExpression |
| 2338 | goto-room | BinaryExpression |
| 2339 | room | CallExpression |
| 2341 | goto-inbox | BinaryExpression |
| 2342 | inbox | CallExpression |
| 2343 | goto-objects | BinaryExpression |
| 2344 | objects | CallExpression |
| 2345 | goto-settings | BinaryExpression |
| 2346 | settings | CallExpression |
| 2347 | new-message | BinaryExpression |
| 2348 | room | CallExpression |
| 2351 | new-work | BinaryExpression |
| 2352 | room | CallExpression |
| 2354 | workflow:work | CallExpression |
| 2355 | new-plan | BinaryExpression |
| 2356 | room | CallExpression |
| 2358 | workflow:plan | CallExpression |
| 2359 | new-review | BinaryExpression |
| 2360 | room | CallExpression |
| 2362 | workflow:review | CallExpression |
| 2363 | new-decision | BinaryExpression |
| 2364 | room | CallExpression |
| 2367 | decision | PropertyAssignment |
| 2372 | workflow | CallExpression |
| 2373 | connect | BinaryExpression |
| 2374 | room | CallExpression |
| 2375 | connect | CallExpression |
| 2376 | msg- | CallExpression |
| 2378 | room | CallExpression |
| 2383 | message- | BinaryExpression |
| 2384 | center | PropertyAssignment |
| 2387 | session- | CallExpression |
| 2389 | room | CallExpression |
| 2393 | object- | CallExpression |
| 2396 | room | CallExpression |
| 2398 | workflow | CallExpression |
| 2421 | work | BinaryExpression |
| 2440 | outbox-status | CallExpression |
| 2442 | sent | BinaryExpression |
| 2443 | failed | BinaryExpression |
| 2443 | cancelled | BinaryExpression |
| 2465 | plan | BinaryExpression |
| 2467 | objective | CallExpression |
| 2468 | steps | CallExpression |
| 2470 | work | BinaryExpression |
| 2472 | title | CallExpression |
| 2473 | owner | CallExpression |
| 2474 | scope | CallExpression |
| 2475 | state | CallExpression |
| 2476 | evidence | CallExpression |
| 2478 | decision | BinaryExpression |
| 2479 | text | CallExpression |
| 2479 | state | CallExpression |
| 2480 | review | BinaryExpression |
| 2482 | artifact | CallExpression |
| 2483 | revision | CallExpression |
| 2484 | base | CallExpression |
| 2485 | owner | CallExpression |
| 2486 | pending | PropertyAssignment |
| 2487 | checks | CallExpression |
| 2498 | alert | JsxAttribute / role |
| 2507 | work | JsxAttribute / value |
| 2508 | plan | JsxAttribute / value |
| 2509 | decision | JsxAttribute / value |
| 2510 | review | JsxAttribute / value |
| 2513 | plan | BinaryExpression |
| 2518 | objective | JsxAttribute / name |
| 2527 | steps | JsxAttribute / name |
| 2534 | decision | BinaryExpression |
| 2538 | text | JsxAttribute / name |
| 2542 | state | JsxAttribute / name |
| 2542 | proposed | BinaryExpression |
| 2548 | small | JsxAttribute / className |
| 2555 | work | BinaryExpression |
| 2560 | title | JsxAttribute / name |
| 2568 | scope | JsxAttribute / name |
| 2576 | artifact | JsxAttribute / name |
| 2582 | form-grid | JsxAttribute / className |
| 2586 | revision | JsxAttribute / name |
| 2594 | base | JsxAttribute / name |
| 2599 | checks | JsxAttribute / name |
| 2601 | small | JsxAttribute / className |
| 2608 | review | BinaryExpression |
| 2610 | owner | JsxAttribute / name |
| 2624 | work | BinaryExpression |
| 2628 | state | JsxAttribute / name |
| 2628 | proposed | BinaryExpression |
| 2645 | evidence | JsxAttribute / name |
| 2655 | primary wide | JsxAttribute / className |
| 2662 | root | CallExpression |

## Proposed glossary (owner approval required)

| User word | Code word | Boundary |
|---|---|---|
| Agent | Session participant | A connected participant, not a newly launched model process |
| Conversation | native session | The exact existing conversation inside an agent app |
| Connection | binding | Association between that conversation, this Mac and one room |
| Connection type | connector/app adapter | Delivery mechanism; advanced setup may name MCP or Codex queue |
| This Mac / device | node/device | Local installation; do not call device setup “create a room” |
| Room | room/channel | Named collaboration space, not device pairing or the whole app |
| Room host | hub | Hosting Mac/server; infrastructure term only in advanced details |
| Message to room | board post, targets=[] | Broadcast/local room visibility, not guaranteed individual read confirmation |
| Direct message | message with targets | Exact addressed conversation |
| Plan / Work request / Review / Decision | object kinds | Prefer specific kind to generic “object”, “workflow” or “packet” |
| Delivery status | receipt state | Distinguish queued/submitted from confirmed reading |
| Read confirmation | acknowledged receipt | Explicit receiving-agent acknowledgement |
| Working / Idle / Blocked / Done | self-reported presence | Must say self-reported; not proof a process is alive |

### Terminology exceptions index

Every candidate copy occurrence is indexed in the visible table; rows marked Naming,
Developer term, Infrastructure wording, Overloaded room or Advanced precision are the
occurrence-level exception list. Repeated labels retain all source locations. Specific
mismatches: Connect agent vs Connect a conversation vs Connect conversation; Plan vs
Shared plan; Review vs Review packet; Plans & work vs Shared planning; Inbox vs Open
requests; Room settings for app settings; node hosting/pairing described as room creation.
“Residents” is a code concept, not current main.tsx visible copy. Generic “objects” and
“workflow” are mostly implementation names, but raw object kind fallback can leak claim.
Advanced commands and wire values MUST NOT be mechanically renamed with the glossary.

## Dynamic text and compositions

| Text / pattern | Where | Verdict | Proposed replacement |
|---|---|---|---|
| {room.title}, fallback General or raw room ID | roomName :124–125, sidebar, breadcrumb, connection/request room | Keep title; raw fallback technical | Room unavailable when title cannot be resolved; expose ID in details |
| {session.title}, {device.name}, {snapshot.name} | authors, participants, requests, connections, settings, recipient options | User-controlled; keep | Escape/render as text; do not replace user names |
| {appName} · {model} · {device_name} | IdentityChip, palette, selects | Keep identity; long/unknown strings | Separate model/app/delivery mode; retain full details in accessible text |
| Raw app fallback | appName :130–136 | Developer value can leak pull/connector code | Unknown connection type; show raw value in details |
| Raw receipt state fallback | receiptName :180–193 | Unknown backend status exposed | Unknown delivery status; raw value in details |
| Raw object kind / state / verdict | palette hint :278, work/review/decision cards, Workflow title/button | Wire values / claim editor mismatch | Display map with sentence-case labels; unsupported kind read-only |
| {count}, v{version}, Version {version}, Revision {revision} | sidebar, inbox, cards, context | Keep counts, clarify scope | Version {version}; distinguish per-room vs across-Mac counts |
| {author}, {message text}, {reply excerpt}, {search query} | palette, conversation, reply preview, empty search | User/agent content, unbounded values | Preserve content; distinguish deleted source from empty message |
| {objective}, {steps}, {title}, {scope}, {artifact}, {checks}, {evidence}, {text} | object cards and forms | User/agent content | Preserve values; humanize field labels only |
| Accepted by {session/device/raw ID} | decision cards/context | Raw ID fallback technical | Accepted by unavailable participant, ID in details |
| {native ID}, {binding ID}, {request device ID} | setup details, connection metadata, Inbox requests | Advanced identifiers | Hide behind details/copy action; preserve exact IDs |
| Invitation ID and masked single-use proof | pairing dialog | Sensitive, necessary | Keep; never log or include real examples in review |
| {backup path}, {runtime.hub_port} | success banner, private hub command | Necessary local values | Success notice / Advanced setup; no concrete credentials captured |
| Locale time/date; author initial | message metadata/avatar | Keep | Unchanged; full date tooltip already present |
| Owner: {title or exact session}; evidence/base/reviewer fragments | object cards | Naming and inconsistent prefix casing | Owner / Evidence / Base version / Reviewer consistently |
| No matches for “{q}”. / No messages match “{query}”. | palette/room | Keep scoped distinction | Unchanged |
| Update {kind}, Save {kind} | Workflow | Raw kind and wrong generic new title | Update/Save plan, work request, review, decision via display map |
| {error}, {connectionError}, {saveError}, {outbox.error}, {receipt.reason} | alert, form, Inbox, receipt tooltip | External strings / Error: prefix / raw validation | Friendly action-specific summary + technical details; preserve rejection cause |

## Claims, omissions and tooltip findings

All proof **read in code**, not new runtime observations.

1. **False reconnect claim** (:2303): same native conversation can reactivate existing
   identity (desktop/protocol.py bind). Propose “Disconnect this conversation? You can
   reconnect it later.” Do not promise a new identity.
2. **Review save reset understated** (:2602 vs :2480–2488): text says changing artifact
   resets approval, but every UI save writes pending and empty findings. Fix behavior or
   warn that saving resets review; wording alone cannot preserve approval.
3. **Message needs attention** (:1332) labels every failed outbox kind, including object
   saves. First fix batch added inline rejection but did not relabel historical Inbox errors.
4. **Saved locally before sending** (:1796) is unconditional composer help, even when
   helper failure means draft was not persisted. New offline notice is accurate but this
   older reassurance can contradict it. Suggested: “Sent messages are saved locally.
   Unsent drafts stay in this window.” No persistence promise until enqueue succeeds.
5. **All new workflows named New request** (:2456), including plans and decisions.
6. **Hardcoded examples**: brand 01, build 0.1.0, model placeholder claude-opus-4-8,
   release-review placeholder, task UUID / ses_… example, My Mac / My other Mac.
   Generic Mac examples are fine; model example is unverified and ses_ belongs to retired
   connector. Do not confuse sample placeholder with a real bound identity.
7. **Empty states**: Connections has no explicit empty-list text, devices/pairing have no
   empty-state guidance, completed work has no empty message. Inbox empty copy can ignore
   the other kinds it displays; Plans & work empty copy omits reviews/decisions.
8. **Success feedback**: request-to-join remains open without explicit submitted/waiting
   approval copy; backup success is in error banner. Theme and pause selections show state,
   not separate confirmation; do not add needless toast noise for every toggle.
9. **Tooltips**: pause/resume title duplicates aria-label (acceptable accessible name, no
   extra explanation). Bound room is developer wording. Presence title repeats displayed
   state rather than last-report age. Full timestamp title is useful. Icon context toggle,
   Room settings, add plan/work/decision and reply cancel have aria-labels but no visible
   hover explanation. Close/error X buttons also use aria-label, not title; not unlabeled.
10. **Shortcut copy**: ⌘ K/⌘K spacing varies, esc lower-case; room-filter ⌘K opens palette,
    not that input. Use platform-aware shortcut formatting and label the actual action.
11. **Infrastructure instructions**: raw MCP flags, Tailscale command, allowlist flag and
    plugin paths belong in Advanced setup. Preserve exact syntax; move rather than blindly
    paraphrase. Retired OpenCode instructions should be removed in the approved cleanup.
12. **Phase boundary**: presence truth/expiry and retired-code reachability remain Phase 5;
    error swallowing, accessibility implementation and component split remain Phase 6.

## Other shipped UI strings

| Text | Where | Verdict | Proposed replacement |
|---|---|---|---|
| Agent Room | index.html title; tauri.conf.json product/window title | Keep | Unchanged |
| Unsupported action | native main.rs:16 | Technical | This action is not available in this version. |
| Starting local helper… | main.rs:17 | Infrastructure | Starting Agent Room… |
| Helper is restarting | main.rs:17 | Infrastructure | Reconnecting to Agent Room… |
| Helper port missing / Helper connection missing | main.rs:18–19 | Technical | Cannot connect to Agent Room. Restart the app; details available. |
| Connection unavailable | main.rs:20 | Vague | Cannot connect to Agent Room. |
| Local helper is reconnecting. Saved messages are retained. | main.rs:21 | Intent not proved | Cannot reach the local service. Previously saved messages remain on this Mac. |
| Invalid helper response | main.rs:22 | Technical | Agent Room returned an unreadable response. Retry or restart. |
| Home directory unavailable | main.rs:32 | Technical | Cannot find your user folder. |
| App executable unavailable | main.rs:39 | Technical | Cannot locate the app for login startup. |
| Install the app bundle before enabling login startup | main.rs:40 | Keep, clearer | Install Agent Room in Applications before enabling startup at login. |
| Unable to create login entry / Unable to save login entry / Unable to remove Agent Room login entry | main.rs:42–45 | Implementation term | Could not enable/disable startup at login. Check permissions. |
| Unable to start Agent Room | main.rs:72 | Keep | Unchanged (native fatal path, not a React banner). |
| Manual updates; signed release service not configured | runtime_info main.rs:28 | Not rendered currently | Exclude from current visible copy; keep tracked as runtime metadata. |
| Local helper unavailable | vite.config.ts proxy error | Infrastructure | Cannot reach Agent Room’s local service. |
| Request rejected. Check exact session, pairing, fields and revision. | desktop_main.py control error | Too many unrelated remedies | Action-specific validation message; retain safe details. |
| Operation unavailable; local messages are retained. | desktop_main.py control error | Scope unclear | Cannot complete this action. Previously saved messages are retained. |

CSS only supplies an empty pseudo-element content string; no nonempty generated copy.
Native framework/OS default menus and arbitrary network/OS exception texts cannot be
exhaustively enumerated from this repo; no claim of native runtime verification is made.

## Backend-origin validation strings

These can surface through outbox.reason/error when protocol submission is rejected.
The following conservative extraction lists literal require()/ValueError messages from
node.py and protocol.py. Some are agent-only or API-only, not guaranteed frontend paths;
keeping their source locations avoids silently missing a user-visible rejection. Verdict
for each: technical validation; replacement is a contextual human summary plus exact
technical detail, not an unsafe blanket promise of retry or delivery.

| Text | Where | Verdict | Proposed replacement |
|---|---|---|---|
| remote hub requires HTTPS | desktop/node.py:28 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| use a hub origin without credentials or path | desktop/node.py:29 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| unknown protocol action | desktop/node.py:80 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| redirect refused; confirm the hub URL | desktop/node.py:23 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| device schema newer than app | desktop/node.py:91 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| device credential missing in Keychain | desktop/node.py:147 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| device already configured | desktop/node.py:156 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| device name required | desktop/node.py:157 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| use a separate device profile to join another hub | desktop/node.py:170 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| create or join a room first | desktop/node.py:191 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| room id required | desktop/node.py:192 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| room not granted to this device | desktop/node.py:195 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| create or join a room first | desktop/node.py:201 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| create or join a room first | desktop/node.py:208 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| session already connected in another room; remove it first | desktop/node.py:237 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| create or join a room first | desktop/node.py:250 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| event too large | desktop/node.py:258 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| session is not bound on this device | desktop/node.py:271 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| invalid presence state | desktop/node.py:289 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| unsupported app | desktop/node.py:328 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| native session identity required | desktop/node.py:329 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| title too long | desktop/node.py:330 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| model name too long | desktop/node.py:331 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| native bridge identity mismatch | desktop/node.py:590 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| connector generation changed; reconnect exact native session | desktop/node.py:591 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| stale bridge lease | desktop/node.py:618 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| delivery does not belong to bridge | desktop/node.py:620 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| invalid native send result | desktop/node.py:621 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| unknown room tool | desktop/node.py:720 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| unknown local action | desktop/node.py:850 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| OpenCode requires its exact existing local directory | desktop/node.py:229 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| native workspace binding is immutable | desktop/node.py:241 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| OpenCode requires its exact existing local directory | desktop/node.py:333 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| no connection request for this session | desktop/node.py:351 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| bridge superseded; reconnect exact native session | desktop/node.py:605 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| wait requires exact active identity and generation | desktop/node.py:644 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| binding not found | desktop/node.py:787 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| saved operation not found | desktop/node.py:806 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| stale bridge lease | desktop/node.py:822 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| watch requires exact active pull identity and generation | desktop/node.py:830 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| native identity or connector generation changed | desktop/node.py:846 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| hub response exceeds protocol byte limit | desktop/node.py:44 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| local idempotency ID reused for different content | desktop/node.py:262 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| outbox full; reconnect or cancel unsent messages | desktop/node.py:264 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| read a complete page before acknowledging | desktop/node.py:691 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| receipt exceeds offered complete page | desktop/node.py:702 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| message already sending; cannot recall a submitted prompt | desktop/node.py:814 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| stale or missing native bridge lease | desktop/node.py:848 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| receipt message was not offered in a complete page | desktop/node.py:695 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| hub schema newer than this app; preserve data and upgrade | desktop/protocol.py:60 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| device authentication required | desktop/protocol.py:95 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| device revoked | desktop/protocol.py:103 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| room not granted | desktop/protocol.py:106 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| device name required | desktop/protocol.py:116 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| canonical device identity required | desktop/protocol.py:117 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| strong device credential required | desktop/protocol.py:135 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| room name required | desktop/protocol.py:192 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| room name required | desktop/protocol.py:203 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| unsupported adapter | desktop/protocol.py:211 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| exact native session required | desktop/protocol.py:212 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| conversation title required | desktop/protocol.py:213 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| sender binding or generation invalid | desktop/protocol.py:242 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| unsupported protocol version | desktop/protocol.py:245 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| stable event ID required | desktop/protocol.py:246 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| invalid or oversized event | desktop/protocol.py:248 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| unsupported event kind | desktop/protocol.py:249 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| object ID and data required | desktop/protocol.py:303 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| unsupported collaboration object | desktop/protocol.py:304 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| object room/type immutable | desktop/protocol.py:306 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| stale object version; refresh before editing | desktop/protocol.py:308 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| valid replay cursor required | desktop/protocol.py:357 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| invalid snapshot cursor | desktop/protocol.py:377 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| hub already initialized | desktop/protocol.py:87 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| device revoked or credential invalid | desktop/protocol.py:98 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| trusted administrator required | desktop/protocol.py:105 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| pairing expired or invalid | desktop/protocol.py:120 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| pairing already claimed | desktop/protocol.py:121 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| device already exists | desktop/protocol.py:122 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| no pending pairing | desktop/protocol.py:129 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| pairing not approved or expired | desktop/protocol.py:138 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| cannot revoke your own administrator | desktop/protocol.py:152 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| device revoked | desktop/protocol.py:194 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| invalid room identity | desktop/protocol.py:196 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| room already exists | desktop/protocol.py:197 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| room not found | desktop/protocol.py:206 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| canonical Codex task UUID required | desktop/protocol.py:215 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| OpenCode native session ID required | desktop/protocol.py:217 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| work title and valid state required | desktop/protocol.py:311 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| work owner must be an exact room session | desktop/protocol.py:312 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| pairing already redeemed | desktop/protocol.py:142 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| idempotency ID reused for different event | desktop/protocol.py:257 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| message text required | desktop/protocol.py:260 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| invalid exact targets | desktop/protocol.py:262 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| self-delivery is not allowed; post to the board instead | desktop/protocol.py:263 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| create a new work request to reassign; preserve original ownership | desktop/protocol.py:314 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| only assigned owner can advance work | desktop/protocol.py:316 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| completion evidence required | desktop/protocol.py:318 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| immutable artifact, revision and base required | desktop/protocol.py:320 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| review verdict required | desktop/protocol.py:321 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| exact reviewer required | desktop/protocol.py:322 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| invalid snapshot offset | desktop/protocol.py:391 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| stale connector generation | desktop/protocol.py:230 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| room delivery queue full; resolve pending work first | desktop/protocol.py:266 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| agent message rate limit reached; pause and let the person respond | desktop/protocol.py:269 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| target session is not active in this room | desktop/protocol.py:272 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| reply source missing or in another room | desktop/protocol.py:275 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| receipt requires exact receiving session | desktop/protocol.py:280 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| invalid receipt state | desktop/protocol.py:282 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| receipt target does not belong to message | desktop/protocol.py:284 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| invalid receipt revision | desktop/protocol.py:288 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| reviewer is immutable | desktop/protocol.py:324 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| only exact reviewer can give a verdict | desktop/protocol.py:328 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| checks and findings required | desktop/protocol.py:329 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| decision text and state required | desktop/protocol.py:332 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| changed artifact invalidates previous approval | desktop/protocol.py:326 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| objective and plan steps required | desktop/protocol.py:339 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| claim needs scope and bounded lease | desktop/protocol.py:341 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |
| only claim owner may renew or release | desktop/protocol.py:343 | Technical validation; reachability varies | Explain failed action; retain this cause in details. |

## Review outcome

Phase 4 is a source-based copy review only. Proposed terminology awaits owner selection in the final fix batches. No copy, styles, backend behavior, installed app or live data changed. Tests: 187 passed in 26.76s; desktop tsc --noEmit exit 0. Next: Phase 5 only.
