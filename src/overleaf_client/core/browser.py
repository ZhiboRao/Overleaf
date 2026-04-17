"""QtWebEngine profile and page wrappers.

QtWebEngine Profile 与 Page 封装。

The browser profile is the single source of truth for cookies, local
storage, downloads, and cache. We keep it on disk under the application
support directory so that login state survives app restarts. Downloads
are routed to the user-configured directory (``~/Downloads`` by default).

浏览器 Profile 是 Cookie、localStorage、下载、缓存的唯一持久化点，
我们将其放在应用数据目录，从而在重启后保持登录态。下载文件会被
送到用户配置的目录（默认 ``~/Downloads``）。
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtWebEngineCore import (
    QWebEngineDownloadRequest,
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
)

from overleaf_client import APP_NAME, __version__
from overleaf_client.core.config import ConfigManager

_LOGGER = logging.getLogger(__name__)


def build_user_agent() -> str:
    """Return a desktop-style user agent string.

    返回桌面风格的 User-Agent。
    """
    # Overleaf gates certain features on desktop-class UA detection; the
    # default Qt UA is fine but we append an app marker for telemetry.
    # Overleaf 会根据 UA 启用桌面功能；默认 Qt UA 已可用，我们追加
    # 一段应用标识便于后端观测。
    return (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 "
        f"{APP_NAME.replace(' ', '')}/{__version__}"
    )


class OverleafProfile(QWebEngineProfile):
    """Persistent QtWebEngine profile used by every page in the app.

    应用内所有页面共享的持久化 QtWebEngine Profile。
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        parent: QObject | None = None,
    ) -> None:
        """Initialize the profile.

        Args:
            config_manager: Source of app configuration and on-disk paths.
            parent: Optional QObject parent.
        """
        # Giving the profile a stable storage name makes it persistent.
        # 指定固定 storage name 即声明为持久化 Profile。
        super().__init__("overleaf-client-profile", parent)
        self._config_manager = config_manager

        profile_dir = config_manager.profile_dir
        self.setCachePath(str(profile_dir / "cache"))
        self.setPersistentStoragePath(str(profile_dir / "storage"))
        self.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies,
        )
        self.setHttpUserAgent(build_user_agent())
        self.setSpellCheckEnabled(True)

        settings = self.settings()
        for attr in (
            QWebEngineSettings.WebAttribute.LocalStorageEnabled,
            QWebEngineSettings.WebAttribute.PluginsEnabled,
            QWebEngineSettings.WebAttribute.JavascriptEnabled,
            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
            QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard,
            QWebEngineSettings.WebAttribute.FullScreenSupportEnabled,
            QWebEngineSettings.WebAttribute.PdfViewerEnabled,
            QWebEngineSettings.WebAttribute.AllowRunningInsecureContent,
        ):
            settings.setAttribute(attr, True)

        self.downloadRequested.connect(self._on_download_requested)

    @Slot(QWebEngineDownloadRequest)
    def _on_download_requested(
        self, download: QWebEngineDownloadRequest,
    ) -> None:
        """Route downloads to the configured directory.

        将下载文件送到用户配置的目录。
        """
        cfg = self._config_manager.config
        target_dir = Path(cfg.download_dir) if cfg.download_dir else (
            Path.home() / "Downloads"
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        download.setDownloadDirectory(str(target_dir))
        _LOGGER.info(
            "Download started: %s -> %s",
            download.downloadFileName(),
            target_dir,
        )
        download.accept()


class OverleafPage(QWebEnginePage):
    """Page that forwards new-window navigations to the owning window.

    将新窗口请求转发给宿主窗口处理的 Page。

    Signals:
        new_window_requested: Emitted when the page wants to open a URL in
            a new window (e.g. target="_blank" link, window.open).
    """

    new_window_requested = Signal(QUrl)

    def __init__(
        self,
        profile: OverleafProfile,
        parent: QObject | None = None,
    ) -> None:
        """Initialize the page bound to the shared profile.

        Args:
            profile: Shared persistent profile.
            parent: Optional QObject parent.
        """
        super().__init__(profile, parent)

    def createWindow(  # noqa: N802 - Qt override
        self, _window_type: QWebEnginePage.WebWindowType,
    ) -> QWebEnginePage | None:
        """Intercept ``window.open`` / target="_blank" navigations.

        拦截 ``window.open`` / target="_blank" 跳转。
        """
        # We cannot synchronously construct a window here without creating
        # a retain cycle; instead we create a disposable page, wait for
        # the URL, emit it, then let Qt dispose the page.
        # 这里不能同步创建窗口，否则会产生循环引用。改为创建一个
        # 临时 Page，拿到 URL 后发信号并交由 Qt 回收。
        staging = OverleafPage(
            profile=self.profile() if isinstance(
                self.profile(), OverleafProfile,
            ) else None,  # type: ignore[arg-type]
            parent=self,
        )
        staging.urlChanged.connect(self.new_window_requested)
        return staging
