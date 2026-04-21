#!/usr/bin/env bash
# Clean the repository of build artifacts, caches, and transient files.
# 清理仓库中的构建产物、缓存与临时文件。
#
# Usage:
#   ./clean.sh            # standard clean
#   ./clean.sh --deep     # also remove .venv/ (forces a fresh install.sh run)
#
# Standard clean removes:
#   - build/, dist/ (py2app output)
#   - *.egg-info/  (setuptools metadata)
#   - __pycache__/, *.pyc, *.pyo (Python bytecode, excluding .venv/)
#   - .mypy_cache/, .ruff_cache/, .pytest_cache/ (tool caches)
#   - .DS_Store (macOS Finder metadata, excluding .venv/)
#
# --deep additionally removes:
#   - .venv/       (virtual environment; recreate via install.sh / make venv)

set -euo pipefail

say() { printf "\033[1;36m==>\033[0m %s\n" "$*"; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

DEEP=0
case "${1:-}" in
    ""|"--shallow") DEEP=0 ;;
    "--deep") DEEP=1 ;;
    *) echo "Unknown flag: $1 (use --deep)" >&2; exit 2 ;;
esac

say "Removing build / dist artifacts"
rm -rf build dist

say "Removing egg-info"
rm -rf ./*.egg-info src/*.egg-info

say "Removing Python bytecode caches"
# Excluding .venv/ keeps the installed interpreter intact so a plain
# clean doesn't require re-running pip install.
# 排除 .venv/，避免清理后还得重新装依赖。
find . -type d -name '__pycache__' -not -path './.venv/*' -print0 \
    | xargs -0 rm -rf
find . -type f \( -name '*.pyc' -o -name '*.pyo' \) \
    -not -path './.venv/*' -delete

say "Removing lint / type caches"
rm -rf .mypy_cache .ruff_cache .pytest_cache

say "Removing macOS metadata"
find . -name '.DS_Store' -not -path './.venv/*' -delete

if [[ "$DEEP" -eq 1 ]]; then
    say "Deep clean: removing .venv/"
    rm -rf .venv
fi

say "Done / 清理完毕"
