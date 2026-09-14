#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
# Builder prerequisites: Python 3.12, Node 20+, pnpm and Rust 1.88+.
# Installed users need none of them; PyInstaller bundles the Python runtime.
BUILD_PYTHON=${BUILD_PYTHON:-python3}
"$BUILD_PYTHON" -m venv work/build-env
work/build-env/bin/python -m pip install -r requirements-desktop.txt
work/build-env/bin/python -m PyInstaller --noconfirm --onedir --name agent-room-helper \
  --hidden-import keyring.backends.macOS --hidden-import desktop.mcp \
  --hidden-import desktop.recovery --hidden-import desktop.legacy --hidden-import roomd \
  --add-data ui.html:. --add-data icon.png:. \
  --distpath apps/desktop/src-tauri/binaries --workpath work/pyinstaller desktop_main.py
cd apps/desktop
pnpm install --frozen-lockfile
pnpm build
# Sign the complete app, including the frozen helper and its libraries, before
# Tauri creates the DMG. Local builds use ad-hoc signing; distribution builds
# may supply their Developer ID identity and notarization credentials.
export APPLE_SIGNING_IDENTITY="${APPLE_SIGNING_IDENTITY:--}"
pnpm tauri build --bundles app,dmg
