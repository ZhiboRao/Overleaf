"""py2app packaging entry point.

py2app 打包入口。

Usage:
    python setup.py py2app            # release bundle / 发布版
    python setup.py py2app -A         # alias build (dev iteration) / 开发版

Only used on macOS. Regular pip installs read metadata from
``pyproject.toml`` instead.

仅在 macOS 上使用；普通 pip 安装依赖 ``pyproject.toml`` 中的元数据。
"""

from __future__ import annotations

import sys
from pathlib import Path

from setuptools import setup

if sys.platform != "darwin":
    sys.exit("setup.py (py2app) is only supported on macOS.")

ROOT = Path(__file__).parent.resolve()
ICON_ICNS = ROOT / "resources" / "icon.icns"

APP = ["src/overleaf_client/__main__.py"]

OPTIONS = {
    "argv_emulation": False,
    "iconfile": str(ICON_ICNS) if ICON_ICNS.exists() else None,
    "plist": {
        "CFBundleName": "Overleaf Client",
        "CFBundleDisplayName": "Overleaf Client",
        "CFBundleIdentifier": "com.zhiborao.overleafclient",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
        "NSHumanReadableCopyright": "© 2026 ZhiboRao. MIT License.",
        "NSAppTransportSecurity": {
            "NSAllowsArbitraryLoads": True,
        },
    },
    "packages": ["overleaf_client", "PySide6"],
    "includes": ["keyring", "keyring.backends"],
    "resources": [str(ROOT / "resources")],
}

setup(
    name="Overleaf Client",
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app>=0.28"],
    package_dir={"": "src"},
)
