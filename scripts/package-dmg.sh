#!/bin/sh
# Package the verified app without Finder automation or an interactive desktop.
set -eu
cd "$(dirname "$0")/.."
bundle_dir=apps/desktop/src-tauri/target/release/bundle
app_bundle="$bundle_dir/macos/Agent Room.app"
codesign --verify --deep --strict "$app_bundle"
app_version=$(/usr/libexec/PlistBuddy -c 'Print CFBundleShortVersionString' "$app_bundle/Contents/Info.plist")
architecture=$(uname -m)
mkdir -p "$bundle_dir/dmg" work
stage=$(mktemp -d "$PWD/work/dmg-stage.XXXXXX")
trap 'rm -rf "$stage"' EXIT HUP INT TERM
ditto "$app_bundle" "$stage/Agent Room.app"
ln -s /Applications "$stage/Applications"
hdiutil create -ov -format UDZO -volname 'Agent Room' -srcfolder "$stage" \
  "$bundle_dir/dmg/Agent Room_${app_version}_${architecture}.dmg"
hdiutil verify "$bundle_dir/dmg/Agent Room_${app_version}_${architecture}.dmg"
