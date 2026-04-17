"""Main application window.

应用主窗口。
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QSize, Qt, QUrl, Slot
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QSystemTrayIcon,
    QToolBar,
    QWidget,
)

from overleaf_client import APP_NAME
from overleaf_client.core.browser import OverleafPage, OverleafProfile
from overleaf_client.core.config import ConfigManager
from overleaf_client.core.credentials import Credential, CredentialStore
from overleaf_client.core.network import NetworkMonitor
from overleaf_client.ui.notifications import Notifier
from overleaf_client.ui.preferences import PreferencesDialog
from overleaf_client.ui.shortcuts import (
    DOWNLOAD_PDF_JS,
    RECOMPILE_JS,
    login_autofill_js,
)

_LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Primary browser window hosting the Overleaf web app.

    承载 Overleaf Web App 的主浏览器窗口。
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        credential_store: CredentialStore,
        profile: OverleafProfile,
        app_icon: QIcon,
        on_badge_change: Callable[[str | None], None] | None = None,
    ) -> None:
        """Initialize the main window.

        Args:
            config_manager: App configuration source.
            credential_store: Secure credential provider.
            profile: Persistent browser profile.
            app_icon: Icon used for window / tray.
            on_badge_change: Optional callback for Dock badge updates.
                Called with ``None`` to clear or a short label to set.
        """
        super().__init__()
        self._config_manager = config_manager
        self._credential_store = credential_store
        self._profile = profile
        self._on_badge_change = on_badge_change

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon)
        self.resize(QSize(1280, 860))

        self._view = QWebEngineView(self)
        self._page = OverleafPage(profile, self._view)
        self._page.new_window_requested.connect(self._open_external_window)
        self._view.setPage(self._page)
        self._view.setZoomFactor(config_manager.config.zoom_factor)
        self.setCentralWidget(self._view)

        self._tray = QSystemTrayIcon(app_icon, self)
        self._tray.setToolTip(APP_NAME)
        self._tray.show()
        self._notifier = Notifier(tray=self._tray)

        self._status = QStatusBar(self)
        self.setStatusBar(self._status)
        self._status.showMessage("Loading… / 正在加载…", 3_000)

        self._toolbar = self._build_toolbar()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self._toolbar)

        self._monitor = NetworkMonitor(
            config_manager.config.home_url, parent=self,
        )
        self._monitor.online_changed.connect(self._on_network_changed)
        self._monitor.start()

        self._view.loadFinished.connect(self._on_load_finished)
        self._view.urlChanged.connect(self._on_url_changed)
        self._view.titleChanged.connect(self._on_title_changed)

        self._view.load(QUrl(config_manager.config.home_url))

    # ---------------------------------------------------------------- Toolbar
    def _build_toolbar(self) -> QToolBar:
        toolbar = QToolBar("Main", self)
        toolbar.setMovable(False)

        def _add(text: str, handler: Callable[[], None],
                 shortcut: QKeySequence | None = None) -> QAction:
            action = QAction(text, self)
            if shortcut is not None:
                action.setShortcut(shortcut)
            action.triggered.connect(handler)
            toolbar.addAction(action)
            self.addAction(action)  # keeps shortcut active without focus
            return action

        _add("Back / 后退", self._view_action_back,
             QKeySequence(QKeySequence.StandardKey.Back))
        _add("Forward / 前进", self._view_action_forward,
             QKeySequence(QKeySequence.StandardKey.Forward))
        _add("Reload / 刷新", lambda: self._view.reload(),
             QKeySequence(QKeySequence.StandardKey.Refresh))
        toolbar.addSeparator()
        _add("Home / 首页", self._go_home)
        _add("Recompile / 编译", self.trigger_recompile,
             QKeySequence("Ctrl+S"))
        _add("Download PDF / 下载 PDF", self.download_pdf,
             QKeySequence("Ctrl+D"))
        return toolbar

    def _view_action_back(self) -> None:
        self._view.back()

    def _view_action_forward(self) -> None:
        self._view.forward()

    def _go_home(self) -> None:
        self._view.load(QUrl(self._config_manager.config.home_url))

    # ------------------------------------------------------------- Shortcuts
    @Slot()
    def trigger_recompile(self) -> None:
        """Click the Overleaf "Recompile" button via JS injection.

        通过 JS 注入点击 Overleaf「Recompile」按钮。
        """
        self._page.runJavaScript(RECOMPILE_JS, self._on_recompile_result)

    def _on_recompile_result(self, ok: object) -> None:
        if ok:
            self._status.showMessage("Recompile triggered / 已触发编译", 3_000)
        else:
            self._status.showMessage(
                "Recompile button not found / 未找到编译按钮", 5_000,
            )

    @Slot()
    def download_pdf(self) -> None:
        """Trigger Overleaf's "Download PDF" action. / 触发「下载 PDF」。"""
        self._page.runJavaScript(DOWNLOAD_PDF_JS)

    # ------------------------------------------------------------- Callbacks
    @Slot(bool)
    def _on_load_finished(self, ok: bool) -> None:
        if not ok:
            self._notifier.notify(
                APP_NAME, "Page failed to load / 页面加载失败",
            )
            return
        # If we're on a login page, offer to autofill from Keychain.
        # 若当前在登录页，从钥匙串取出凭据自动填充。
        if "/login" in self._view.url().toString():
            self._try_autofill_login()

    @Slot(QUrl)
    def _on_url_changed(self, url: QUrl) -> None:
        self._status.showMessage(url.toString(), 2_000)

    @Slot(str)
    def _on_title_changed(self, title: str) -> None:
        self.setWindowTitle(f"{title} — {APP_NAME}" if title else APP_NAME)

    @Slot(bool)
    def _on_network_changed(self, online: bool) -> None:
        message = (
            "Back online / 已恢复网络"
            if online else "You appear to be offline / 网络已断开"
        )
        self._status.showMessage(message, 5_000)
        if self._config_manager.config.enable_notifications:
            self._notifier.notify(APP_NAME, message)
        if self._on_badge_change is not None:
            self._on_badge_change(None if online else "!")

    @Slot(QUrl)
    def _open_external_window(self, url: QUrl) -> None:
        """Open link in a new internal window rather than a system browser.

        新建一个应用内窗口加载链接，而非委派到系统浏览器。
        """
        child = MainWindow(
            config_manager=self._config_manager,
            credential_store=self._credential_store,
            profile=self._profile,
            app_icon=self.windowIcon(),
            on_badge_change=self._on_badge_change,
        )
        child._view.load(url)
        child.show()

    # -------------------------------------------------------------- Login UX
    def _try_autofill_login(self) -> None:
        cred = self._credential_store.load()
        if cred is None:
            return
        self._page.runJavaScript(
            login_autofill_js(cred.username, cred.password),
        )

    def prompt_save_credentials(self) -> None:
        """Ask the user whether to save credentials to the Keychain.

        询问用户是否将凭据保存至钥匙串。
        """
        if not self._config_manager.config.autosave_credentials:
            return
        email, ok = QInputDialog.getText(
            self, APP_NAME,
            "Email (leave empty to skip) / 邮箱（留空则跳过）:",
            QLineEdit.EchoMode.Normal,
        )
        if not ok or not email:
            return
        password, ok = QInputDialog.getText(
            self, APP_NAME,
            "Password / 密码:",
            QLineEdit.EchoMode.Password,
        )
        if not ok or not password:
            return
        if self._credential_store.save(Credential(email, password)):
            self._notifier.notify(
                APP_NAME, "Credentials saved to Keychain / 凭据已保存",
            )
        else:
            QMessageBox.warning(
                self, APP_NAME,
                "Could not save to Keychain. / 无法写入钥匙串。",
            )

    def open_preferences(self) -> None:
        """Show the preferences dialog. / 打开偏好设置对话框。"""
        dlg = PreferencesDialog(
            self._config_manager, self._credential_store, parent=self,
        )
        if dlg.exec() == PreferencesDialog.DialogCode.Accepted:
            self._view.setZoomFactor(self._config_manager.config.zoom_factor)

    # --------------------------------------------------------------- Qt hooks
    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Persist window state then accept. / 保存窗口状态后关闭。"""
        event.accept()
