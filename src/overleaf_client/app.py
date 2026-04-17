"""Application entry point.

应用入口。

This module wires the core (config, credentials, profile, network) to the
UI (main window, menu bar, notifications) and to platform integrations
(Dock badge on macOS). Keep this file thin — it is the composition root.

本文件将核心层（配置、凭据、Profile、网络）接到 UI 层（主窗口、菜单、
通知）以及平台集成层（Dock 徽标）。本文件应尽量纤薄，只作组合入口。
"""

from __future__ import annotations

import logging
import signal
import sys
from importlib import resources
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtGui import QIcon
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWidgets import QApplication, QMenuBar, QMessageBox

from overleaf_client import APP_BUNDLE_ID, APP_NAME, __version__
from overleaf_client.core.browser import OverleafPage, OverleafProfile
from overleaf_client.core.config import ConfigManager
from overleaf_client.core.credentials import CredentialStore
from overleaf_client.platforms.mac.dock import DockBadge
from overleaf_client.ui.downloads import DownloadsPanel
from overleaf_client.ui.main_window import MainWindow
from overleaf_client.ui.menu_bar import build_menu_bar
from overleaf_client.ui.styles import apply_modern_style

_LOGGER = logging.getLogger(__name__)


class _OverleafApplication(QApplication):
    """QApplication that re-shows the main window on Dock-icon activation.

    点击 Dock 图标（或 ``Cmd-Tab`` 切回应用）时重新显示主窗口的
    QApplication 子类。主窗口关闭只是隐藏，所以需要这个入口把它唤回来。

    macOS delivers :attr:`QEvent.Type.ApplicationActivate` to the
    application itself (not any widget), so subclassing ``QApplication``
    and overriding :meth:`event` is the canonical hook.
    """

    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self._main_window: MainWindow | None = None

    def set_main_window(self, window: MainWindow) -> None:
        """Register the window to reveal on re-activation."""
        self._main_window = window

    def event(self, e: QEvent) -> bool:
        if e.type() == QEvent.Type.ApplicationActivate:
            win = self._main_window
            if win is not None and not win.isVisible():
                win.show()
                win.raise_()
                win.activateWindow()
        return super().event(e)


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _load_icon() -> QIcon:
    """Load the packaged application icon, falling back to a blank icon.

    加载打包内置的应用图标，若缺失则返回空图标占位。
    """
    try:
        icon_path = resources.files("overleaf_client").joinpath(
            "resources/icon.png",
        )
        # resources.files returns a Traversable; resolve to real path.
        # resources.files 返回 Traversable，需要读到真实路径。
        with resources.as_file(icon_path) as real_path:
            return QIcon(str(real_path))
    except (FileNotFoundError, ModuleNotFoundError, AttributeError):
        alt = Path(__file__).parent.parent.parent / "resources" / "icon.png"
        if alt.exists():
            return QIcon(str(alt))
        _LOGGER.warning("Icon not found; using empty icon.")
        return QIcon()


def main(argv: list[str] | None = None) -> int:
    """Run the Overleaf Client event loop.

    运行 Overleaf 客户端事件循环。

    Args:
        argv: Optional ``sys.argv``-style argument list.

    Returns:
        Process exit code.
    """
    _configure_logging()
    argv = list(sys.argv if argv is None else argv)

    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setApplicationVersion(__version__)
    QCoreApplication.setOrganizationDomain(APP_BUNDLE_ID)

    app = _OverleafApplication(argv)
    app.setApplicationDisplayName(APP_NAME)
    # Main window "close" hides instead of quitting; only Cmd+Q or the
    # app menu's Quit action should terminate the app. Without this,
    # Qt would still quit if we ever emit a real close.
    # 主窗口关闭只是隐藏；只有 Cmd+Q / 菜单退出才会真正退出。
    app.setQuitOnLastWindowClosed(False)

    icon = _load_icon()
    app.setWindowIcon(icon)

    config_manager = ConfigManager()
    apply_modern_style(
        app,
        base_pt=config_manager.config.ui_font_size,
        toolbar_pad_y=config_manager.config.ui_toolbar_padding,
    )
    credential_store = CredentialStore()
    profile = OverleafProfile(config_manager, parent=app)
    dock_badge = DockBadge()

    downloads_panel = DownloadsPanel()
    downloads_panel.setWindowIcon(icon)
    downloads_panel.setWindowOpacity(
        config_manager.config.window_opacity / 100.0,
    )
    profile.download_requested.connect(downloads_panel.track)

    def _update_badge(label: str | None) -> None:
        if config_manager.config.enable_dock_badge:
            dock_badge.set_label(label)

    window = MainWindow(
        config_manager=config_manager,
        credential_store=credential_store,
        profile=profile,
        app_icon=icon,
        on_badge_change=_update_badge,
        downloads_panel=downloads_panel,
    )

    # Keep child windows alive for the life of the app; without this the
    # MainWindow returned by the factory below would be garbage collected
    # as soon as the factory returns, tearing its page down before Qt gets
    # a chance to load the ``window.open`` target.
    # 保留子窗口引用，否则工厂一返回 MainWindow 就会被 GC，导致 Qt
    # 还没来得及加载 ``window.open`` 目标页面就被销毁。
    child_windows: list[MainWindow] = []

    def _new_window_factory() -> QWebEnginePage | None:
        child = MainWindow(
            config_manager=config_manager,
            credential_store=credential_store,
            profile=profile,
            app_icon=icon,
            on_badge_change=_update_badge,
            skip_initial_load=True,
            downloads_panel=downloads_panel,
            hide_on_close=False,
        )
        child_windows.append(child)
        child.show()
        return child._page  # noqa: SLF001

    OverleafPage.set_new_window_factory(_new_window_factory)

    app.set_main_window(window)

    # On macOS a single shared menu bar lives at the top of the screen.
    # macOS 上顶部系统菜单栏由单一共享 QMenuBar 驱动。
    menu_bar = QMenuBar(parent=None)

    def _on_about() -> None:
        QMessageBox.about(
            window, APP_NAME,
            f"<b>{APP_NAME}</b> v{__version__}<br><br>"
            "Unofficial macOS desktop client for Overleaf.<br>"
            "Overleaf 的非官方 macOS 桌面客户端。<br><br>"
            "<a href='https://github.com/ZhiboRao/Overleaf'>GitHub</a>",
        )

    def _on_quit() -> None:
        app.quit()

    def _on_toggle_fullscreen() -> None:
        if window.isFullScreen():
            window.showNormal()
        else:
            window.showFullScreen()

    build_menu_bar(
        menu_bar,
        on_open_preferences=window.open_preferences,
        on_reload=lambda: window._view.reload(),  # noqa: SLF001
        on_toggle_fullscreen=_on_toggle_fullscreen,
        on_save_credentials=window.prompt_save_credentials,
        on_about=_on_about,
        on_quit=_on_quit,
    )
    # Attach to window so the menu bar shows on non-macOS too.
    # 同时挂到窗口上，非 macOS 平台也能看到菜单。
    window.setMenuBar(menu_bar)

    # Allow Ctrl+C in terminal to cleanly tear down the app.
    # 允许终端 Ctrl+C 正常退出应用。
    signal.signal(signal.SIGINT, lambda *_: app.quit())

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
