"""Overleaf macOS desktop client package.

Overleaf macOS 桌面客户端包。

Attributes:
    __version__: Semantic version string.
    APP_NAME: Human-readable application name.
    APP_BUNDLE_ID: Reverse-DNS bundle identifier used on macOS.
    DEFAULT_HOME_URL: Default Overleaf site loaded on startup.
"""

from __future__ import annotations

__version__ = "0.1.0"

APP_NAME = "Overleaf Client"
APP_BUNDLE_ID = "com.zhiborao.overleafclient"
DEFAULT_HOME_URL = "https://cn.overleaf.com/"
