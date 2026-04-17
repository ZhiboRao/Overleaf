"""Application configuration and on-disk paths.

应用配置管理与本地存储路径。

The configuration lives in ``~/Library/Application Support/Overleaf Client``
on macOS. Settings are persisted as JSON; the QtWebEngine browser profile
(cookies, cache, local storage) is persisted alongside them under a
dedicated sub-directory.

配置文件存放在 macOS 的
``~/Library/Application Support/Overleaf Client`` 目录；
浏览器 Profile（Cookie、缓存、localStorage）存放在相邻子目录。
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from overleaf_client import APP_NAME, DEFAULT_HOME_URL

_LOGGER = logging.getLogger(__name__)


def _default_support_dir() -> Path:
    """Return the platform-appropriate support directory.

    返回各平台推荐的应用数据目录。

    Returns:
        Absolute path to the per-user application support directory.
    """
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / APP_NAME
    if sys.platform.startswith("win"):
        return home / "AppData" / "Roaming" / APP_NAME
    return home / ".config" / APP_NAME.lower().replace(" ", "-")


@dataclass
class AppConfig:
    """User-editable application settings.

    用户可编辑的应用设置。

    Attributes:
        home_url: Initial URL loaded when the app starts.
        zoom_factor: WebEngine zoom factor (1.0 = 100%).
        enable_notifications: Whether system notifications fire on events.
        enable_dock_badge: Whether the macOS dock badge is enabled.
        autosave_credentials: Whether to offer to save credentials in
            the system keychain.
        download_dir: Default download directory for PDFs/artifacts. If
            ``None``, falls back to ``~/Downloads``.
        ui_language: Preferred Overleaf deployment. ``"zh"`` routes to
            ``cn.overleaf.com`` (the Chinese-language site, typically
            faster in mainland China); ``"en"`` routes to
            ``www.overleaf.com`` (English). ``"auto"`` uses ``home_url``
            unchanged so self-hosted deployments keep working.
        ui_font_size: Base font point size applied app-wide via the
            global stylesheet. Downstream sizes (titles, hints,
            download percentages) scale proportionally.
        window_opacity: Opacity (percent, 50–100) of the Preferences
            dialog and the Downloads panel. 100 means fully opaque.
        ui_toolbar_padding: Top/bottom padding (px, 2–14) for
            main-window toolbar buttons (Back / Forward / Reload /
            Home / Downloads) — smaller values produce a thinner
            toolbar row.
    """

    home_url: str = DEFAULT_HOME_URL
    zoom_factor: float = 1.0
    enable_notifications: bool = True
    enable_dock_badge: bool = True
    autosave_credentials: bool = True
    download_dir: str | None = None
    ui_language: str = "auto"
    ui_font_size: int = 16
    window_opacity: int = 95
    ui_toolbar_padding: int = 4


class ConfigManager:
    """Load and persist :class:`AppConfig` as JSON.

    负责将 :class:`AppConfig` 以 JSON 形式读写到磁盘。
    """

    _CONFIG_FILENAME = "settings.json"
    _PROFILE_DIRNAME = "webengine-profile"

    def __init__(self, support_dir: Path | None = None) -> None:
        """Initialize the manager.

        Args:
            support_dir: Override the application support directory (mostly
                for tests). Defaults to the platform-appropriate location.
        """
        self._support_dir = support_dir or _default_support_dir()
        self._support_dir.mkdir(parents=True, exist_ok=True)
        self._config_path = self._support_dir / self._CONFIG_FILENAME
        self._config: AppConfig = self._load()

    @property
    def config(self) -> AppConfig:
        """Return the current :class:`AppConfig` / 返回当前配置对象."""
        return self._config

    @property
    def support_dir(self) -> Path:
        """Return the application support directory / 返回应用数据目录."""
        return self._support_dir

    @property
    def profile_dir(self) -> Path:
        """Directory used by QtWebEngine to persist profile data.

        QtWebEngine Profile 持久化目录。
        """
        path = self._support_dir / self._PROFILE_DIRNAME
        path.mkdir(parents=True, exist_ok=True)
        return path

    def update(self, **changes: Any) -> AppConfig:
        """Merge field updates and persist.

        合并字段更新并写入磁盘。

        Args:
            **changes: Keyword arguments matching :class:`AppConfig` fields.

        Returns:
            The updated configuration.

        Raises:
            AttributeError: If a key does not correspond to an
                :class:`AppConfig` field.
        """
        for key, value in changes.items():
            if not hasattr(self._config, key):
                raise AttributeError(f"Unknown config key: {key}")
            setattr(self._config, key, value)
        self._save()
        return self._config

    def _load(self) -> AppConfig:
        if not self._config_path.exists():
            cfg = AppConfig()
            self._config = cfg
            self._save()
            return cfg
        try:
            raw = json.loads(self._config_path.read_text("utf-8"))
            known = {
                f: raw[f]
                for f in AppConfig.__dataclass_fields__
                if f in raw
            }
            return AppConfig(**known)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            _LOGGER.warning(
                "Config file corrupt (%s); falling back to defaults.", exc,
            )
            return AppConfig()

    def _save(self) -> None:
        try:
            self._config_path.write_text(
                json.dumps(asdict(self._config), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            _LOGGER.error("Failed to persist config: %s", exc)
