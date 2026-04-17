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

import ctypes.util
import subprocess
import sys
import sysconfig
from pathlib import Path

from setuptools import setup

if sys.platform != "darwin":
    sys.exit("setup.py (py2app) is only supported on macOS.")


# Only import py2app when the ``py2app`` command is actually being run.
# pip's PEP 517 build isolation evaluates this file to collect metadata
# without installing setup_requires, so a top-level import would fail.
#
# 仅在真正执行 ``py2app`` 命令时才导入 py2app。pip 的 PEP 517 构建
# 会在未安装 setup_requires 的隔离环境下执行本文件，顶层导入会报错。
_RUNNING_PY2APP = "py2app" in sys.argv


def _py2app_cmdclass() -> dict[str, type]:
    # py2app >= 0.28 refuses to build when ``install_requires`` is set,
    # but setuptools auto-populates it from pyproject.toml's
    # ``[project.dependencies]``. We clear it just before py2app runs.
    #
    # py2app >= 0.28 拒绝处理带 install_requires 的项目；setuptools
    # 会从 pyproject.toml 中自动填入。此处在 py2app 真正运行前清空。
    from py2app.build_app import py2app as _base  # noqa: N813

    class _Py2App(_base):  # type: ignore[misc, valid-type]
        def finalize_options(self) -> None:
            self.distribution.install_requires = None
            super().finalize_options()

    return {"py2app": _Py2App}


ROOT = Path(__file__).parent.resolve()
ICON_ICNS = ROOT / "resources" / "icon.icns"

APP = ["src/overleaf_client/__main__.py"]


def _discover_libffi() -> list[str]:
    """Return an absolute path list for libffi.8.dylib, or empty on miss.

    返回 libffi.8.dylib 的绝对路径列表；未找到则为空。

    Conda/Anaconda Pythons link _ctypes.so against ``@rpath/libffi.8.dylib``
    but py2app does not resolve that rpath, producing "Library not loaded"
    at launch. Bundling the dylib via the ``frameworks`` option fixes it.

    Conda/Anaconda 的 _ctypes.so 通过 ``@rpath/libffi.8.dylib`` 引用
    libffi；py2app 不会跟随 rpath 复制它，导致 .app 启动时报
    "Library not loaded"。显式加入 ``frameworks`` 即可修复。
    """
    candidates: list[Path] = []

    # 1) Same prefix as the Python being used to build.
    prefix = Path(sysconfig.get_config_var("prefix") or sys.prefix)
    candidates.append(prefix / "lib" / "libffi.8.dylib")

    # 2) Shared lib resolved by ctypes.
    found_by_ctypes = ctypes.util.find_library("ffi")
    if found_by_ctypes:
        candidates.append(Path(found_by_ctypes))

    # 3) Well-known Homebrew locations.
    candidates.extend([
        Path("/opt/homebrew/opt/libffi/lib/libffi.8.dylib"),
        Path("/usr/local/opt/libffi/lib/libffi.8.dylib"),
    ])

    # 4) Parse `otool -L` on _ctypes.so and resolve the @rpath entry.
    try:
        import _ctypes
        otool = subprocess.run(
            ["otool", "-L", _ctypes.__file__],
            check=True, capture_output=True, text=True,
        )
        for line in otool.stdout.splitlines():
            if "libffi.8.dylib" in line and "@rpath" in line:
                # Try each rpath directory sibling of the Python prefix.
                candidates.append(prefix / "lib" / "libffi.8.dylib")
                break
    except (FileNotFoundError, subprocess.CalledProcessError, ImportError):
        pass

    for c in candidates:
        if c.is_file():
            return [str(c.resolve())]
    return []

def _py2app_options() -> dict[str, object]:
    return {
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
        "resources": [str(ROOT / "resources")],
        "frameworks": _discover_libffi(),
    }


_setup_kwargs: dict[str, object] = {
    "name": "Overleaf Client",
    "app": APP,
    "setup_requires": ["py2app>=0.28"],
    "package_dir": {"": "src"},
}
if _RUNNING_PY2APP:
    _setup_kwargs["options"] = {"py2app": _py2app_options()}
    _setup_kwargs["cmdclass"] = _py2app_cmdclass()

setup(**_setup_kwargs)
