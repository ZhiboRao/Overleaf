#!/usr/bin/env python3
"""Build a macOS ``icon.icns`` bundle from ``resources/icon.png``.

从 ``resources/icon.png`` 构建 macOS ``icon.icns`` 图标包。

Requires the ``sips`` and ``iconutil`` CLIs shipped with macOS.

依赖 macOS 自带的 ``sips`` 与 ``iconutil`` 命令。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

_SIZES = [16, 32, 64, 128, 256, 512, 1024]

_RESOURCES = Path(__file__).resolve().parent.parent / "resources"
_SRC_PNG = _RESOURCES / "icon.png"
_OUT_ICNS = _RESOURCES / "icon.icns"


def _require(tool: str) -> None:
    if shutil.which(tool) is None:
        sys.exit(
            f"error: '{tool}' not found (this script must run on macOS)."
        )


def main() -> int:
    """Build ``icon.icns`` from ``icon.png``."""
    if sys.platform != "darwin":
        print("skip: icon.icns only needed on macOS.", file=sys.stderr)
        return 0
    if not _SRC_PNG.exists():
        sys.exit(f"error: source icon missing: {_SRC_PNG}")

    _require("sips")
    _require("iconutil")

    iconset = _RESOURCES / "icon.iconset"
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir()

    for size in _SIZES:
        target = iconset / f"icon_{size}x{size}.png"
        subprocess.run(
            ["sips", "-z", str(size), str(size),
             str(_SRC_PNG), "--out", str(target)],
            check=True, capture_output=True,
        )
        if size <= 512:
            retina = iconset / f"icon_{size}x{size}@2x.png"
            subprocess.run(
                ["sips", "-z", str(size * 2), str(size * 2),
                 str(_SRC_PNG), "--out", str(retina)],
                check=True, capture_output=True,
            )

    subprocess.run(
        ["iconutil", "-c", "icns", str(iconset), "-o", str(_OUT_ICNS)],
        check=True,
    )
    shutil.rmtree(iconset)
    print(f"wrote {_OUT_ICNS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
