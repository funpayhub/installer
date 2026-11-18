#!/usr/bin/env bash
# Packs the Linux executable made by build.py (dist/dothub-installer) into dist/dothub-installer-x86_64.AppImage
#
# Usage: .github/scripts/build-appimage.sh <path to appimagetool>
# build.py has to run first: it also writes build/icon.png

set -euo pipefail

TOOL="$(realpath "$1")"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APPDIR="$ROOT/build/AppDir"
NAME="dothub-installer"

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
install -m 755 "$ROOT/dist/$NAME" "$APPDIR/usr/bin/$NAME"
ln -s "usr/bin/$NAME" "$APPDIR/AppRun"
cp "$ROOT/build/icon.png" "$APPDIR/$NAME.png"
cat > "$APPDIR/$NAME.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=.hub Installer
Name[ru]=Установщик .hub
Comment=Installs .hub on this computer or on a Linux server
Comment[ru]=Устанавливает .hub на этот компьютер или на Linux-сервер
Exec=$NAME
Icon=$NAME
Categories=Utility;
Terminal=false
EOF

ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$TOOL" --no-appstream "$APPDIR" "$ROOT/dist/$NAME-x86_64.AppImage"
