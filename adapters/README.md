# Local OpenCode bridge

The plugin uses OpenCode's supplied authenticated SDK client. It never starts
another server or conversation or exports a password. Development typecheck is
against `@opencode-ai/plugin` 1.18.30; installed older hosts need their own live
acceptance check. `prompt_async` HTTP 204 is **submission**, never agent receipt.

The installable app includes these files at `Contents/Resources/adapters/`.

1. In Agent Room, connect **OpenCode**, its exact `ses_…` ID, title and directory.
2. At a convenient session boundary, copy `agent-room-desktop.ts` and the
   `agent-room-desktop/` support folder together into that workspace's `.opencode/plugins/`.
   OpenCode must provide `@opencode-ai/plugin` (add it to the workspace's
   `.opencode/package.json` dependencies if the host requires it).
3. Reload the plugin using your host's supported lifecycle. Keep/resume the same
   native session. Do not start `opencode serve` as a workaround.
4. The plugin matches the local directory and only exact opted-in native IDs.
   It supplies `desktop_room_read`, `desktop_room_post`, `desktop_room_ack`,
   `desktop_room_context`, and `desktop_room_workflow` tools. Use these for
   desktop messages; existing `room_*` tools may still address the live v2 room.
5. Send a synthetic message from Agent Room, confirm the agent explicitly calls
   `desktop_room_ack` after reading, and replies using `reply_to`. A submitted
   receipt, session-idle event, or native API response is insufficient proof.

The plugin is installed on the build Mac in `~/.config/opencode/plugins/`. Its
helper lives in the nested `agent-room-desktop/` folder so the host does not
auto-load that support module as another plugin. The old global Agent Room MCP
entry has been removed. A safe plugin reload and actual receipt/reply are required
before calling an existing session connected; consult `VERIFICATION.md`.
The renderer `window.api.awaitInitialization()` integration is deliberately not
used: external access to that IPC is unproven and would expose a rotating secret.

Busy sessions wait; a race into native busy handling is conservatively uncertain.
Lost responses are never resubmitted automatically. A superseded bridge lease
cannot claim more work. Reconnect retains its native ID and unread cursor.
