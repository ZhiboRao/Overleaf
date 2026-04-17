#!/usr/bin/env bash
# One-click installer for Overleaf Client on macOS.
# macOS 上的一键安装脚本。
#
# What it does:
#   1. Verifies Python >= 3.10.
#   2. Creates .venv and installs runtime dependencies.
#   3. Builds the macOS .app bundle via py2app.
#   4. (Optional) Builds a DMG if `create-dmg` is available.
#   5. Copies the .app into /Applications.
#
# 运行内容：
#   1. 检查 Python >= 3.10。
#   2. 创建 .venv 并安装运行依赖。
#   3. 使用 py2app 构建 macOS .app。
#   4. 若已安装 create-dmg 则顺带生成 DMG。
#   5. 将 .app 复制到 /Applications。

set -euo pipefail

say() { printf "\033[1;36m==>\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m!!\033[0m %s\n" "$*"; }
die() { printf "\033[1;31mxx\033[0m %s\n" "$*" >&2; exit 1; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

[[ "$(uname -s)" == "Darwin" ]] || die "This installer targets macOS only."

PY_BIN="${PYTHON:-python3}"
command -v "$PY_BIN" >/dev/null 2>&1 || die "python3 not found on PATH."

PY_VER="$("$PY_BIN" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
PY_OK="$("$PY_BIN" - <<'PY'
import sys
print("ok" if sys.version_info >= (3, 10) else "bad")
PY
)"
[[ "$PY_OK" == "ok" ]] || die "Python >= 3.10 required (found $PY_VER)."
say "Using Python $PY_VER ($PY_BIN)"

say "Creating virtual environment in .venv"
"$PY_BIN" -m venv .venv
# shellcheck source=/dev/null
source .venv/bin/activate

say "Installing dependencies"
pip install --upgrade pip >/dev/null
pip install -e '.[mac,build]'

say "Building icon.icns"
python scripts/build_icon.py

say "Building .app bundle via py2app"
rm -rf build dist
python setup.py py2app

APP_PATH="dist/Overleaf Client.app"
[[ -d "$APP_PATH" ]] || die "Build did not produce $APP_PATH"

if command -v create-dmg >/dev/null 2>&1; then
    say "Building DMG (create-dmg detected)"
    make dmg || warn "DMG build failed; continuing."
else
    warn "create-dmg not installed; skipping DMG. (brew install create-dmg)"
fi

TARGET="/Applications/Overleaf Client.app"
if [[ -d "$TARGET" ]]; then
    say "Removing previous $TARGET"
    rm -rf "$TARGET"
fi
say "Installing to $TARGET"
cp -R "$APP_PATH" "$TARGET"

say "Done. Launch from Spotlight: \"Overleaf Client\" / 安装完成，Spotlight 搜索 'Overleaf Client' 即可打开。"
