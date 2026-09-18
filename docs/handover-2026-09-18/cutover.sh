#!/bin/bash
# Agent Room — GATED cutover (owner runs this; writing to /Applications is classifier-blocked for the agent).
# Swaps the installed app for the freshly-built feat/overnight-build bundle (room_wait + frontend fixes).
# Reversible: the old bundle and the old data dir are BACKED UP (not deleted) to your Desktop.
set -euo pipefail

NEW="$HOME/Code/agent-room-app/apps/desktop/src-tauri/target/release/bundle/macos/Agent Room.app"
INSTALLED="/Applications/Agent Room.app"
DATA="$HOME/Library/Application Support/Agent Room"
TS="$(date +%Y%m%d-%H%M%S)"

[ -d "$NEW" ] || { echo "New bundle not found at: $NEW" >&2; exit 1; }
codesign --verify --deep --strict "$NEW" || { echo "New bundle fails codesign; aborting." >&2; exit 1; }

echo "1/6 Quit the running app + helper"
osascript -e 'tell application "Agent Room" to quit' 2>/dev/null || true
sleep 2
pkill -f 'Agent Room.app/Contents/Resources/helper/agent-room-helper' 2>/dev/null || true
sleep 1

echo "2/6 Back up the OLD bundle -> Desktop (reversible)"
if [ -d "$INSTALLED" ]; then ditto "$INSTALLED" "$HOME/Desktop/AgentRoom-old-bundle-$TS.app"; fi

echo "3/6 Move the OLD data dir aside -> Desktop (reversible; forces a clean re-init)"
if [ -d "$DATA" ]; then mv "$DATA" "$HOME/Desktop/AgentRoom-old-data-$TS"; fi

echo "4/6 Swap in the NEW bundle"
rm -rf "$INSTALLED"
ditto "$NEW" "$INSTALLED"
codesign --verify --deep --strict "$INSTALLED" && echo "   codesign OK"

echo "5/6 Delete stale Keychain items (old-binary ACL, err -25320). Optional cleanup; new helper mints its own."
for SVC in app.agentroom.desktop.2d0aec2e6d50fd579aa7e5c1 app.agentroom.desktop.f2f9c1b2afaf2f15d577c7e4; do
  security delete-generic-password -s "$SVC" >/dev/null 2>&1 && echo "   removed $SVC" || true
done

echo "6/6 Relaunch"
open "$INSTALLED"
echo "DONE. New app launching (fresh setup screen). Tell the agent 'relaunched' — it will reconnect the 3 agents and run the coordination test."
