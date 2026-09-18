# Phase 2 — control inventory

Reviewed 2026-09-18, product source at 4fd3d3c. No product code changed.

## Evidence and scope

Read all 2,624 lines of apps/desktop/src/main.tsx and traced its control calls to
 desktop/node.py:738–824, plus object validation in desktop/protocol.py:301–339.
Line references below are main.tsx unless prefixed otherwise.

**Proof for every row: read in code.** No browser clicks were performed in this
phase. The result column explicitly describes traced behavior, not an observed
click. “works” means the control has a coherent implementation for valid inputs,
not that native integration, delivery, or browser behavior was end-to-end tested.
API probes are recorded separately; they are not “clicked” evidence. Conditional
controls are not dead merely because the current fixture cannot display them.

One row per distinct control/command; repeated data-driven rows are inventoried
by template, not once per seeded record. Shared dialog controls apply to every
Dialog instance. Form submission also covers Enter in its ordinary text inputs.
Select choices are listed in their field row; static text is distinguished below.
Backend column: **local** = React/HTML only; **yes** = node.control dispatch exists;
**native** = Tauri handler exists. Fields call the indicated action only on save.

## Inventory (source order, with palette commands beside the palette)

| View / source | Visible label | Handler → control action | Backend handler exists? | Result when clicked / used (code trace, not clicked) | Verdict |
|---|---|---|---|---|---|
| Palette 298–303 | Search messages, participants, plans or jump… | setQ; filter actions | local | Filters labels, hints and groups; resets cursor | works |
| Palette 304–309 | ArrowDown / ArrowUp | setCursor | local | Moves selection, clamps to available results | works |
| Palette 310–315 | Enter | execute(cursor) → onExecute | local | Runs selected command; empty results do nothing intentionally | works |
| Palette 314–315 | Escape | onClose | local | Closes palette when input handles key | works |
| Palette 290–295 | Outside list / cancel | onCancel or wrapper target check → onClose | local | Wrapper-only click closes; nonmodal dialog has no modal backdrop; outside dismissal not established | works but confusing |
| Palette 329–332 | Result row hover | setCursor(i) | local | Changes keyboard selection | works |
| Palette 237; 2334 | Go to room | setView(room); setQuery(empty) | local | Shows current room, not a room chooser | works |
| Palette 238; 2337 | Go to inbox | setView(inbox) | local | Opens Inbox | works |
| Palette 239; 2339 | Go to plans & work | setView(objects) | local | Opens object list | works |
| Palette 240; 2341 | Settings · connections and device | setView(settings) | local | Opens Settings | works |
| Palette 241; 2343 | Message the room… | setView(room); clear query; delayed focus | local | Focuses composer but preserves a previously selected recipient | works but confusing |
| Palette 242; 2347 | New work request | clear editing; workflow:work | local | Opens work form | works |
| Palette 243; 2351 | New shared plan | clear editing; workflow:plan | local | Opens plan form | works |
| Palette 244; 2355 | New review packet | clear editing; workflow:review | local | Opens review form | works |
| Palette 245; 2359 | Record a decision | new decision editing; workflow | local | Opens decision form | works |
| Palette 246; 2369 | Connect a conversation | setView(room); connect dialog | local | Opens binding form | works |
| Palette 248–262; 2372 | Message excerpt (each result) | msg-ID → clear query; scrollIntoView | local | Scrolls to matching message in current room | works |
| Palette 264–274; 2384 | Participant title (each result) | session-ID → setTarget; focus | local | Selects exact recipient and focuses composer | works |
| Palette 275–286; 2390 | Object title (each result) | object-ID → setEditing; workflow | local | Opens matching object; claim objects have no proper editor (see F6) | works but confusing |
| Shared Dialog 384–391 | Backdrop | target === dialog → onClose | local | Closes dialog on backdrop/outer dialog click | works |
| Shared Dialog 387 | Escape | onCancel → onClose | local | Closes modal dialog | works |
| Shared Dialog 394 | Close dialog (X) | onClose | local | Discards unsaved form state | works |
| Global 448–456 | Cmd+K / Ctrl+K | setPalette(true) | local | Opens palette; applies even with another dialog open | works but confusing |
| Global 454–456 | Escape | setQuery(empty); setReply(null) | local | Also clears search and reply even when dismissing another surface | works but confusing |
| Sidebar 589–600 | Inbox | setView(inbox) | local | Opens Inbox; badge counts receipts + requests, unlike Needs you | works but confusing |
| Sidebar 601–610 | Plans & work | setView(objects) | local | Opens active-room objects | works |
| Sidebar 611–619 | Search ⌘ K | setPalette(true) | local | Opens global-in-current-snapshot palette, not room filter | works |
| Sidebar 623–636 | Needs you | setView(inbox); clear query | local | Opens full Inbox, not a filtered smart view | works but confusing |
| Sidebar 650–674 | Room title (each room) | act → room-select {room}; setView | yes :772 | Switches active room if different; clears search but not draft/recipient | works but confusing |
| Sidebar 675 | New room | setDialog(new-room) | local | Opens naming form, even before setup | works but confusing |
| Sidebar 688–695 | Settings | setView(settings) | local | Shows Settings after setup; setup screen otherwise overrides view | works |
| Header 728–735 | Pause delivery / Resume delivery | act → pause {paused} | yes :782 | Toggles device delivery flag | works |
| Header 737–748 | Toggle room context | setContext | local | Toggles panel; visible panel only exists in configured Room view | works but confusing |
| Error banner 753–762 | Dismiss error | clear error and connectionError | local | Hides banner; polling can redisplay ongoing failure | works |
| Setup 806–811 | Create a room | setDialog(create) | local | Opens device hosting setup, not new-room form | works but confusing |
| Setup 812–818 | Join an existing room | setDialog(join) | local | Opens pairing form | works |
| Settings 829–837 | System | setAppearance(system) | local | Removes explicit theme; persists choice in localStorage if available | works |
| Settings 829–837 | Light | setAppearance(light) | local | Sets theme attribute and persists choice | works |
| Settings 829–837 | Dark | setAppearance(dark) | local | Sets theme attribute and persists choice | works |
| Settings 864–873 | Revoke access | act → revoke {device} | yes :761 | Host revokes active other device; no confirmation | works but confusing |
| Settings 876–887 | Pair another Mac | act → pair-create; setPair; pair dialog | yes :761 | Creates invitation, displays proof | works |
| Settings 894–901 | Approve device | act → pair-approve {id} | yes :761 | Approves pending device request | works |
| Settings 909–922 | Start Agent Room at login | invoke set_login_start {enabled} | native main.rs:36,71 | Native-only checkbox; updates runtime or error banner; not available in preview | works |
| Settings 930–937 | Pause delivery / Resume delivery | act → pause {paused} | yes :782 | Same delivery flag as header | works |
| Settings 971–985 | Setup details (each binding) | setEditing(connection); dialog connection | local | Displays identity and connector instructions | works |
| Settings 986–1001 | Remove (each binding) | setEditing(connection); remove-connection | local | Opens confirmation, no removal yet | works |
| Settings 1003–1009 | Connect a conversation | setDialog(connect) | local | Opens binding form | works |
| Settings 1014–1020 | Reconnect with Keychain | act → unlock | yes :739 | Retries vault and wakes worker; shown only offline | works |
| Settings 1027–1036 | Create a consistent backup | act → backup; setError(success path) | yes :744 | Creates backup but reports success in error banner | works but confusing |
| Settings 1038–1048 | Private hub setup (summary) | native HTML details toggle | local | Expands command; gated by runtime.hub_port, normally native only | works |
| Plans & work 1058–1067 | Plan | clear editing; workflow:plan | local | Opens plan form | works |
| Plans & work 1068–1077 | Work request | clear editing; workflow:work | local | Opens work form | works |
| Plans & work 1078–1087 | Review | clear editing; workflow:review | local | Opens review form | works |
| Plans & work 1088–1104 | Decision | new decision editing; workflow:decision | local | Opens decision form | works |
| Plans & work 1114–1131 | Plan objective card | setEditing(o); workflow:plan | local | Opens versioned plan | works |
| Plans & work 1136–1158 | Work title card | setEditing(o); workflow:work | local | Opens versioned work request | works |
| Plans & work 1163–1191 | Review artifact card | setEditing(o); workflow:review | local | Opens review editor, not a verdict form | works but confusing |
| Plans & work 1196–1218 | Decision text card | setEditing(o); workflow:decision | local | Opens versioned decision | works |
| Inbox 1246–1258 | Approve (connection request) | act → request-decide {native,app,approve:true} | yes :759 | Connects requested exact session; disabled while busy | works |
| Inbox 1259–1271 | Decline (connection request) | act → request-decide {native,app,approve:false} | yes :759 | Rejects request; disabled while busy | works |
| Inbox 1292–1320 | Stuck receipt label (each row) | setView(room); setQuery(first 40 chars) | local | Filters conversation by text, not exact message ID | works but confusing |
| Inbox 1353–1387 | Awaiting agents / receipt label | setView(room); clear query; scroll by ID | local | Jumps to message | works |
| Inbox 1390–1406 | Waiting work title | setEditing(o); workflow | local | Opens existing work editor using its kind | works |
| Room 1432–1438 | Connect agent | setDialog(connect) | local | Same form as Connect a conversation | works |
| Room 1450–1457 | Search this room | setQuery | local | Filters text/author; adjacent ⌘K opens palette instead | works but confusing |
| Empty Room 1470–1479 | Start a plan | setText(suggestion); focus composer | local | Drafts a message, does not create a plan object | works but confusing |
| Empty Room 1480–1486 | Request a review | clear editing; workflow without kind | local | Defaults to work, not review (F1) | works but confusing |
| Message 1561–1571 | Reply | setReply; setTarget(sender or board); focus | local | Sets reply and recipient | works |
| Message 1573–1595 | ↳ Reply to excerpt | clear query; scrollIntoView(source ID) | local | Scrolls if source exists; missing source silently does nothing | works but confusing |
| Unsynced message 1677–1686 | Cancel unsent message | act → cancel {id} | yes :785 | Cancels saved outbox item only; race with sending can reject | works |
| Composer 1699–1705 | Cancel reply | setReply(null) | local | Clears reply metadata but retains chosen recipient | works but confusing |
| Composer 1717–1730 | Message recipient: Room board / active session | setTarget | local | Selects board or exact session; disabled while busy | works |
| Composer 1755–1765 | Message | setText; new draftId | local | Updates draft and idempotency ID | works |
| Composer 1767–1773 | Enter | send → act send {id,text,targets,reply_to} | yes :778 | Trims, ignores blank, queues; clears draft after local API success | works |
| Composer 1767–1773 | Shift+Enter | native textarea behavior | local | Inserts newline | works |
| Composer 1710; 1780–1788 | Send message | form submit → send → send | yes :778 | Same as Enter; button disabled when blank/busy | works |
| Context 1805–1811 | Room settings | setView(settings) | local | Opens app/device Settings, no room rename/remove settings | works but confusing |
| Context 1853–1859 | Connect a conversation | setDialog(connect) | local | Opens binding form | works |
| Context 1864–1879 | Add plan | new plan editing; workflow | local | Opens plan form | works |
| Context 1884–1901 | Current plan objective | setEditing(o); workflow | local | Opens plan editor | works |
| Context 1908–1917 | Add work request | clear editing; workflow | local | Defaults to work | works |
| Context 1922–1940 | Work title | setEditing(o); workflow | local | Opens work editor | works |
| Context 1922–1940 | Review artifact | setEditing(o); workflow | local | Opens review editor | works |
| Context 1949–1964 | Add decision | new decision editing; workflow | local | Opens decision form | works |
| Context 1969–1990 | Decision text | setEditing(o); workflow | local | Opens decision editor | works |
| Create dialog 2013–2020 | Device name | form name → create | yes :749 | Required; max 80; names device, not room | works but confusing |
| Create dialog 2021–2023 | Create room | formSubmit → create {name} | yes :749 | Sets up hosting; closes on local success | works but confusing |
| Join dialog 2049 | This device’s name | form name → join-request | yes :751 | Required device name | works |
| Join dialog 2053–2059 | Private hub address | form url → join-request | yes :751 | Required URL; backend applies additional URL rules | works |
| Join dialog 2062 | Invitation ID | form id → join-request | yes :751 | Required invitation identity | works |
| Join dialog 2066 | Pairing proof | form proof → join-request | yes :751 | Required password field, autocomplete off | works |
| Join dialog 2068–2070 | Request to join | formSubmit → join-request {url,id,proof,name}, close=false | yes :751 | Submits and stays open; no explicit success state in form | works but confusing |
| Join dialog 2071–2078 | I’ve approved this Mac — finish pairing | act → join-finish | yes :753 | Attempts completion; rejected if not approved | works |
| Pair dialog 2090 | Invitation ID | readonly input | local | Allows manual selection/copy | works |
| Pair dialog 2094–2100 | Single-use proof | readonly password; onFocus select | local | Selects masked proof for manual copy; no copy button | works but confusing |
| Pair dialog 2106–2114 | View pairing requests | close; setView(settings) | local | Returns to requests in Settings | works |
| New-room dialog 2130–2137 | Room name | form title → room-create | yes :774 | Required, max 80; submit trims whitespace | works |
| New-room dialog 2138–2140 | Create room | formSubmit → room-create {title}; show room | yes :774 | Creates/selects room; whitespace-only title silently returns | works but confusing |
| Connect dialog 2174–2181 | Agent app: Codex / OpenCode / Claude Code / Claude app / MCP | form app → bind | yes :755 | Selects connector; still offers retired OpenCode (F5) | works but confusing |
| Connect dialog 2184–2190 | Conversation title | form title → bind | yes :755 | Required, max 200 | works |
| Connect dialog 2193–2199 | Exact native session ID | form native → bind | yes :755 | Required, max 128; connector-specific validation at backend | works |
| Connect dialog 2202–2205 | Local directory · required for OpenCode | form directory → bind | yes :755 | Not HTML-required; backend validates for OpenCode | works but confusing |
| Connect dialog 2209–2214 | Model · optional | form model → bind | yes :755 | Optional, max 100 | works |
| Connect dialog 2222–2224 | Connect conversation | formSubmit → bind {app,title,native,directory,model} | yes :755 | Binds to current room, opens setup details | works |
| Setup-details dialog 2250 | Native conversation | readonly input | local | Allows manual copy of native identity | works |
| Setup-details dialog 2254 | Desktop room binding | readonly input | local | Allows manual copy of binding identity | works |
| Setup-details dialog 2291–2293 | Done | close dialog | local | Dismisses instructions | works |
| Remove dialog 2302–2308 | Remove connection | act → binding-remove {binding:editing.id} | yes :767 | Removes correct binding; suspect cleared by API probe | works |
| Remove dialog 2309–2315 | Cancel | close dialog | local | Leaves binding unchanged | works |
| Workflow 2465–2475 | Type: Work request / Shared plan / Decision / Review packet | setKind | local | Selects form; disabled for existing version | works |
| Plan form 2480–2486 | Objective | form objective → object | yes :780 | Required objective | works |
| Plan form 2489–2495 | Next steps · one per line | form steps → split newline → object | yes :780 | Required; empty lines removed | works |
| Decision form 2501 | Decision | form text → object | yes :780 | Required text | works |
| Decision form 2505–2509 | Status: proposed / accepted / superseded | form state → object | yes :780 | Protocol records accepting device/agent when accepted | works |
| Work form 2522–2528 | Request | form title → object | yes :780 | Required title | works |
| Work form 2531 | Scope and acceptance | form scope → object | yes :780 | Optional scope | works |
| Review form 2538–2544 | Artifact | form artifact → object | yes :780 | Required artifact | works |
| Review form 2548–2554 | Exact revision | form revision → object | yes :780 | Required revision | works |
| Review form 2557 | Base revision | form base → object | yes :780 | Required base | works |
| Review form 2562 | Checks and test evidence | form checks → object | yes :780 | Optional checks; save also resets verdict/findings (F3) | works but confusing |
| Work form 2572–2586 | Owner: Choose an exact conversation / active sessions | form owner → object | yes :780 | Selects owner; existing owner is immutable at protocol (F2) | errors |
| Review form 2572–2586 | Reviewer: Choose an exact conversation / active sessions | form owner → reviewer → object | yes :780 | Selects reviewer; existing reviewer is immutable at protocol (F2) | errors |
| Work form 2591–2603 | Status: proposed / accepted / working / blocked / ready for review / resolved / cancelled | form state → object | yes :780 | Allows resolved without requiring evidence in form (F2) | works but confusing |
| Work form 2607–2612 | Completion evidence | form evidence → object | yes :780 | Optional HTML field, required by protocol when resolved | works but confusing |
| Workflow 2617 | Save plan | onSave → act object {id,type,version,data} | yes :780 | Queues versioned objective/steps | works |
| Workflow 2617 | Save work | onSave → act object | yes :780 | Queues; ownership/evidence validation can fail asynchronously (F2) | works but confusing |
| Workflow 2617 | Save review | onSave → act object | yes :780 | Always writes pending verdict and empty findings (F3) | works but confusing |
| Workflow 2617 | Save decision | onSave → act object | yes :780 | Queues versioned text/state | works |
| Workflow via claim palette result 2390–2468 | Save claim | onSave → act object with empty data | yes :780 | No claim form branch; invalid claim update queues and is rejected (F6) | errors |

## Non-controls that look actionable / deliberately absent controls

- Sidebar **Active** (637–645) is a static div with a tooltip and count, not a
  navigation button. Verdict **does nothing** as navigation; proof **read in code**.
- Failed outbox rows (1322–1332), completed work rows (1410–1425), participants,
  receipt chips, status dots and breadcrumb are display-only. No retry/dismiss
  failed-send control, participant menu, or completed-work opener here.
- No room rename/remove menu, no device-name editor, no object delete button,
  no review verdict button. Review verdict deliberately belongs to the exact
  reviewer through room tools (protocol.py:327–329).
- Native window/Dock/tray controls are outside this main.tsx inventory.

## Reverse audit — every node.control action without a UI button

The control dispatcher has **28 actions**. Seventeen are called by UI controls:
backup, bind, binding-remove, cancel, create, join-finish, join-request, object,
pair-approve, pair-create, pause, request-decide, revoke, room-create, room-select,
send, unlock. The other eleven follow. Hub-only dispatch in hub_call is not
mistaken for a local control action.

| Action | Backend source / handler | UI use / why no button |
|---|---|---|
| snapshot | node.py:747 → snapshot | Automatic refresh on mount and every 1.8s (:430–447); no refresh button |
| request-create | :757 → request_create | Agent requests admission; UI only approves/declines |
| binding-state | :763 → _resolve_binding_id → set_binding_state | Agent self-report; no human presence setter |
| room-rename | :776 → room_rename | Real management gap: no UI rename control |
| bridge-open | :790 → bridge_open | Connector transport, not a human operation |
| bridge-next | :792 → bridge_next | Connector delivery polling |
| bridge-heartbeat | :794 → lease check / heartbeat | Connector liveness |
| bridge-sent | :800 → bridge_sent | Connector receipt reporting |
| watch-next | :802 → exact pull identity checks / delivery inbox | Watch transport |
| wait-next | :816 → wait_next | Agent long-poll transport |
| tool | :818 → binding / identity checks → tool | Agent tools, including operations not exposed in UI |

Native calls separately: runtime_info is automatic; set_login_start is checkbox-
driven; control is the native API wrapper. There is no room-delete or room-remove
local action in node.py, nor a matching operation found in protocol.py.

## Confirmed code findings (not a Phase 3 journey review)

All findings below have proof **read in code**.

- **F1 — Wrong form from empty-room “Request a review”.** :1481–1483 clears
  editing and opens bare workflow. :2417 initializes kind to work when neither
  editing nor initialKind supplies a kind. The explicit Review button/palette
  command supplies workflow:review and does not have this problem.
- **F2 — Editable fields that the protocol refuses.** :2572–2586 allows changing
  an existing work owner/reviewer; protocol.py:314–315,324 rejects changes.
  Resolved work without evidence is also offered (:2591–2612) but rejected at
  protocol.py:318–319. node.control object (:780) enqueues rather than validating
  these constraints synchronously, so closing the form is not proof of saving.
  The field-level errors verdict applies to those changes, not initial assignment.
- **F3 — Review save resets verdict and findings even with unchanged artifact.**
  :2445–2453 always sends pending and empty findings. Protocol permits a pending
  update; the user cannot preserve a prior verdict through this editor. The text
  only explains changing the artifact resets approval, not every save.
- **F4 — Counts and destinations differ.** Inbox badge (:596–598) uses every
  non-acknowledged receipt plus requests. Needs you (:529–532) uses stuck receipts,
  requests and failed outbox entries. The backend needsYou additionally uses
  blocked bindings (node.py:735). Active is a static counter, and Needs you opens
  full Inbox. These are different measures, not three renderings of one measure.
- **F5 — Retired connector is still offered.** Connect app options (:2176), setup
  text (:786), and setup details (:2240,2256) still expose OpenCode. Backend still
  accepts opencode-bridge (protocol.py:211). Recorded only; no retirement cleanup
  or connector installation attempted in this phase.
- **F6 — Claim palette result reaches an unsupported editor.** Protocol supports
  claim objects (:304,340 onward). Palette includes all snapshot objects (:275),
  then opens Workflow using editing.kind. Workflow has no claim data branch
  (:2430–2453); Save claim submits empty data, which claim validation rejects.
  Conditional path traced only; no claim fixture created or browser click made.
- **F7 — Draft target survives navigation and cancellation.** Room switches
  (:656–660) do not clear target/text/reply. Cancel reply (:1702) only clears reply;
  palette “Message the room” (:2343–2346) also preserves target. A board-sounding
  command can therefore leave a direct-message recipient selected.

## Isolated API probes — not browser clicks

Probed the already-running helper under work/desktop-test using its local control
endpoint; no installed app or live app data was accessed. Credentials were read
in memory/shell variables and are not included here or in committed artifacts.
An earlier shell command unfortunately printed the isolated ready.json into the
session transcript; it must not be copied into repository files.

| Probe | Observed response / conclusion |
|---|---|
| Bind throwaway MCP session, then binding-remove with returned binding ID exactly as UI sends | removed:true; **known wrong-key suspect cleared**. UI :2305 sends binding:editing.id; resolver node.py:279–281 accepts binding directly |
| binding-remove bogus ID / empty data | removed:false; no exception. Do not infer success from HTTP success alone |
| Rename release-work to its existing title | Returned release-work / Release work; backend rename route usable but UI lacks it |
| Set quiet binding to its existing idle state | Returned idle; state route exists |
| Create throwaway request, then decline it | Pending then rejected; original pending request retained |
| Unknown action | Generic “Request rejected. Check exact session, pairing, fields and revision.” |
| Cancel already-failed outbox item | Same generic rejection; saved-only cancellation is intentional in dispatcher |

After cleanup snapshot contained three original local bindings and only the
original seed-pending-01 pending request. **This was not an exact fixture rollback:**
the removed throwaway remained as an inactive hub session in the snapshot and the
rejected request has historical state. Failed outbox count observed was 12, versus
9 in Phase 1; this phase did not establish why it changed. Do not call this state
“restored cleanly” or use the changed count as an independent new defect.

## Coverage limits / pickup

No native login-start, multi-Mac pairing/revocation, clipboard, focus, backdrop,
keyboard or end-to-end delivery behavior was clicked in this phase. Their table
results are code traces, explicitly not empirical “works” claims. Phase 3 remains
the browser journey phase. No control was classified dead solely from being
unavailable in a browser or absent from the current fixture. No fixes performed.
