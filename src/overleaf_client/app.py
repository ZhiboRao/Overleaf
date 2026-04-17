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

from PySide6.QtCore import QCoreApplication, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenuBar, QMessageBox

from overleaf_client import APP_BUNDLE_ID, APP_NAME, __version__
from overleaf_client.core.browser import OverleafProfile
from overleaf_client.core.config import ConfigManager
from overleaf_client.core.credentials import CredentialStore
from overleaf_client.platforms.mac.dock import DockBadge
from overleaf_client.ui.main_window import MainWindow
from overleaf_client.ui.menu_bar import build_menu_bar

_LOGGER = logging.getLogger(__name__)


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

    app = QApplication(argv)
    app.setApplicationDisplayName(APP_NAME)
    app.setQuitOnLastWindowClosed(True)

    icon = _load_icon()
    app.setWindowIcon(icon)

    config_manager = ConfigManager()
    credential_store = CredentialStore()
    profile = OverleafProfile(config_manager, parent=app)
    dock_badge = DockBadge()

    def _update_badge(label: str | None) -> None:
        if config_manager.config.enable_dock_badge:
            dock_badge.set_label(label)

    window = MainWindow(
        config_manager=config_manager,
        credential_store=credential_store,
        profile=profile,
        app_icon=icon,
        on_badge_change=_update_badge,
    )

    # On macOS a single shared menu bar lives at the top of the screen.
    # macOS 上顶部系统菜单栏由单一共享 QMenuBar 驱动。
    menu_bar = QMenuBar(parent=None)

    def _on_new_project() -> None:
        # Overleaf opens the project dashboard at "/project" and offers a
        # "New project" button there. We simply navigate to it.
        # Overleaf 的项目列表位于 "/project"，那里有「新建项目」按钮。
        window._view.load(QUrl(  # noqa: SLF001
            config_manager.config.home_url.rstrip("/") + "/project",
        ))

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
        on_new_project=_on_new_project,
        on_open_preferences=window.open_preferences,
        on_recompile=window.trigger_recompile,
        on_download_pdf=window.download_pdf,
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
