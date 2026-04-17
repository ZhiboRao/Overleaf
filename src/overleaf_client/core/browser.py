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
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWebEngineCore import (
    QWebEngineDownloadRequest,
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
)

from overleaf_client import APP_NAME, __version__
from overleaf_client.core.config import AppConfig, ConfigManager

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


# cn.overleaf.com is a Chinese-only mirror; www.overleaf.com is English.
# Accept-Language can't flip cn's UI, so the language preference instead
# picks which mirror to visit. Hosts that aren't one of these two are
# treated as self-hosted and left alone.
# cn.overleaf.com 只提供中文，www.overleaf.com 默认英文；Accept-Language
# 改不了 cn 站，因此语言选项改为切换 host。非这两个 host 视为自建实例，
# 保持原样。
_CANONICAL_HOSTS: frozenset[str] = frozenset({
    "cn.overleaf.com", "www.overleaf.com", "overleaf.com",
})
_HOST_FOR_LANG: dict[str, str] = {
    "en": "www.overleaf.com",
    "zh": "cn.overleaf.com",
}


def localized_url(url: str, ui_language: str) -> str:
    """Return ``url`` with its host swapped to match ``ui_language``.

    根据 ``ui_language`` 将 ``url`` 的 host 切换到对应的 Overleaf 镜像。

    Non-Overleaf URLs and ``"auto"`` (or any unknown language code) are
    returned unchanged, so self-hosted deployments are not disturbed.
    非 Overleaf 域名及 ``"auto"`` 原样返回，以免影响自建实例。
    """
    target_host = _HOST_FOR_LANG.get(ui_language)
    if target_host is None:
        return url
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in _CANONICAL_HOSTS:
        return url
    netloc = (
        f"{target_host}:{parsed.port}" if parsed.port else target_host
    )
    return urlunparse(parsed._replace(netloc=netloc))


def localized_home_url(cfg: AppConfig) -> str:
    """Return the effective home URL for the current language choice.

    返回当前语言设置对应的首页地址。
    """
    return localized_url(cfg.home_url, cfg.ui_language)


class OverleafProfile(QWebEngineProfile):
    """Persistent QtWebEngine profile used by every page in the app.

    应用内所有页面共享的持久化 QtWebEngine Profile。
    """

    # Emitted after the profile has routed the download to the target
    # directory and accepted it. UI layers (e.g. the downloads panel)
    # subscribe here to track progress for the returned request object.
    # 下载被路由并接受后发出。UI 层（如下载面板）订阅此信号，基于传入的
    # 请求对象追踪进度。
    download_requested = Signal(QWebEngineDownloadRequest)

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
        # Overleaf ships its own spellchecker; leave Qt's off to avoid
        # noisy "qtwebengine_dictionaries not found" warnings.
        # Overleaf 自带拼写检查；这里关闭 Qt 的以避免缺字典时的噪音日志。
        self.setSpellCheckEnabled(False)

        settings = self.settings()
        # Disable Qt's built-in PDF viewer so Overleaf's "Download PDF"
        # (served as application/pdf without Content-Disposition: attachment)
        # reaches the download handler instead of being rendered inline.
        # The editor's preview pane uses PDF.js client-side and is unaffected.
        # 关闭 Qt 自带 PDF 预览器：Overleaf 的 "Download PDF" 返回
        # application/pdf 而不带 Content-Disposition: attachment，若不关
        # 就会被内嵌渲染而不触发下载。左侧编辑预览用的是 PDF.js，不受影响。
        for attr, enabled in (
            (QWebEngineSettings.WebAttribute.LocalStorageEnabled, True),
            (QWebEngineSettings.WebAttribute.PluginsEnabled, True),
            (QWebEngineSettings.WebAttribute.JavascriptEnabled, True),
            (QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True),
            (QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True),
            (QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True),
            (QWebEngineSettings.WebAttribute.PdfViewerEnabled, False),
            (QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True),
        ):
            settings.setAttribute(attr, enabled)

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
        self.download_requested.emit(download)


class OverleafPage(QWebEnginePage):
    """Page backed by the shared profile.

    基于共享 Profile 的 Page。

    ``createWindow`` (invoked by Qt for ``window.open`` / ``target="_blank"``
    / middle-click) must return a fully constructed :class:`QWebEnginePage`
    attached to a visible view — otherwise the new tab loads silently,
    which is why Overleaf's "Download PDF" button used to do nothing. A
    factory callable, registered by the app at startup, creates a real
    child window and returns its page.
    ``createWindow`` 由 Qt 在 ``window.open`` / ``target="_blank"`` / 中键
    点击时调用。若返回的 Page 没绑定可见视图，新窗口就会在后台加载、
    界面上什么也看不到——这正是之前 Overleaf "Download PDF" 无效的根因。
    应用启动时注册一个工厂回调，负责创建真正的子窗口并返回其 Page。
    """

    # Set by the app at startup. Takes no arguments and returns the
    # ``QWebEnginePage`` that Qt should drive the new window with.
    # 启动时注册；不带参数，返回 Qt 用于新窗口的 ``QWebEnginePage``。
    _new_window_factory: Callable[[], QWebEnginePage | None] | None = None

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

    @classmethod
    def set_new_window_factory(
        cls, factory: Callable[[], QWebEnginePage | None] | None,
    ) -> None:
        """Register the factory that :meth:`createWindow` will delegate to.

        注册 :meth:`createWindow` 使用的工厂回调。
        """
        cls._new_window_factory = factory

    def createWindow(  # noqa: N802 - Qt override
        self, _window_type: QWebEnginePage.WebWindowType,
    ) -> QWebEnginePage | None:
        """Produce a real, visible child window for Qt to drive.

        为 Qt 创建真正可见的子窗口。
        """
        factory = OverleafPage._new_window_factory
        if factory is None:
            _LOGGER.warning(
                "new window requested but no factory registered; ignoring",
            )
            return None
        return factory()
