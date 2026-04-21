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
    QApplication,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QSystemTrayIcon,
    QToolBar,
)

from overleaf_client import APP_NAME
from overleaf_client.core import i18n
from overleaf_client.core.browser import (
    OverleafPage,
    OverleafProfile,
    localized_home_url,
    localized_url,
)
from overleaf_client.core.config import ConfigManager
from overleaf_client.core.credentials import Credential, CredentialStore
from overleaf_client.core.network import NetworkMonitor
from overleaf_client.ui.downloads import DownloadsPanel
from overleaf_client.ui.notifications import Notifier
from overleaf_client.ui.preferences import PreferencesDialog
from overleaf_client.ui.shortcuts import login_autofill_js
from overleaf_client.ui.styles import apply_modern_style

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
        *,
        skip_initial_load: bool = False,
        downloads_panel: DownloadsPanel | None = None,
        hide_on_close: bool = True,
        on_language_changed: Callable[[], None] | None = None,
    ) -> None:
        """Initialize the main window.

        Args:
            config_manager: App configuration source.
            credential_store: Secure credential provider.
            profile: Persistent browser profile.
            app_icon: Icon used for window / tray.
            on_badge_change: Optional callback for Dock badge updates.
                Called with ``None`` to clear or a short label to set.
            skip_initial_load: If ``True``, skip loading the home URL.
                Used for child windows where Qt will drive the page itself
                (e.g. ``window.open`` targets handed over via the page
                factory).
            downloads_panel: Shared downloads panel; the toolbar button
                opens this panel. ``None`` hides the toolbar button.
            hide_on_close: If ``True`` (default, used by the primary
                window), clicking the red traffic light hides the
                window instead of closing it — the app keeps running in
                the background and the Dock icon brings it back. Child
                ``window.open`` popups pass ``False`` so they close
                normally.
            on_language_changed: Invoked from Preferences when the UI
                language changes, so the composition root can rebuild
                the menu bar and retranslate peer windows.
        """
        super().__init__()
        self._config_manager = config_manager
        self._credential_store = credential_store
        self._profile = profile
        self._on_badge_change = on_badge_change
        self._downloads_panel = downloads_panel
        self._hide_on_close = hide_on_close
        self._on_language_changed = on_language_changed

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon)
        self.resize(QSize(1280, 860))

        self._view = QWebEngineView(self)
        self._page = OverleafPage(profile, self._view)
        self._view.setPage(self._page)
        self._view.setZoomFactor(config_manager.config.zoom_factor)
        self.setCentralWidget(self._view)

        self._tray = QSystemTrayIcon(app_icon, self)
        self._tray.setToolTip(APP_NAME)
        self._tray.show()
        self._notifier = Notifier(tray=self._tray)

        self._status = QStatusBar(self)
        self.setStatusBar(self._status)
        self._status.showMessage(i18n.t("Loading…"), 3_000)

        self._toolbar_actions: list[tuple[QAction, str, str]] = []
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

        if not skip_initial_load:
            self._view.load(QUrl(localized_home_url(config_manager.config)))

    # ---------------------------------------------------------------- Toolbar
    def _build_toolbar(self) -> QToolBar:
        toolbar = QToolBar("Main", self)
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)

        def _add(
            label_key: str,
            handler: Callable[[], None],
            tooltip_key: str,
            shortcut: QKeySequence | None = None,
        ) -> QAction:
            action = QAction(i18n.t(label_key), self)
            action.setToolTip(i18n.t(tooltip_key))
            if shortcut is not None:
                action.setShortcut(shortcut)
            action.triggered.connect(handler)
            toolbar.addAction(action)
            self.addAction(action)  # keeps shortcut active without focus
            # Remember the source keys so retranslate() can refresh the
            # label / tooltip without rebuilding the toolbar.
            # 记录文案键，让 retranslate() 可以直接刷新而无需重建。
            self._toolbar_actions.append((action, label_key, tooltip_key))
            return action

        # Unicode glyphs serve as mini "icons" so the toolbar reads at a
        # glance without shipping extra image assets.
        # Unicode 字符充当迷你图标，无需额外图像资源即可一眼识别。
        _add("‹  Back", self._view_action_back, "Back",
             QKeySequence(QKeySequence.StandardKey.Back))
        _add("Forward  ›", self._view_action_forward, "Forward",
             QKeySequence(QKeySequence.StandardKey.Forward))
        _add("⟳  Reload", lambda: self._view.reload(), "Reload",
             QKeySequence(QKeySequence.StandardKey.Refresh))
        toolbar.addSeparator()
        _add("⌂  Home", self._go_home, "Home")
        if self._downloads_panel is not None:
            _add("⇣  Downloads", self._show_downloads, "Downloads")
        return toolbar

    def _view_action_back(self) -> None:
        self._view.back()

    def _view_action_forward(self) -> None:
        self._view.forward()

    def _go_home(self) -> None:
        self._view.load(QUrl(localized_home_url(self._config_manager.config)))

    def _show_downloads(self) -> None:
        panel = self._downloads_panel
        if panel is None:
            return
        panel.show()
        panel.raise_()
        panel.activateWindow()

    # ------------------------------------------------------------- Callbacks
    @Slot(bool)
    def _on_load_finished(self, ok: bool) -> None:
        if not ok:
            self._notifier.notify(APP_NAME, i18n.t("Page failed to load"))
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
        message = i18n.t(
            "Back online" if online else "You appear to be offline",
        )
        self._status.showMessage(message, 5_000)
        if self._config_manager.config.enable_notifications:
            self._notifier.notify(APP_NAME, message)
        if self._on_badge_change is not None:
            self._on_badge_change(None if online else "!")

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
            i18n.t("Email (leave empty to skip):"),
            QLineEdit.EchoMode.Normal,
        )
        if not ok or not email:
            return
        password, ok = QInputDialog.getText(
            self, APP_NAME,
            i18n.t("Password:"),
            QLineEdit.EchoMode.Password,
        )
        if not ok or not password:
            return
        if self._credential_store.save(Credential(email, password)):
            self._notifier.notify(
                APP_NAME, i18n.t("Credentials saved to Keychain"),
            )
        else:
            QMessageBox.warning(
                self, APP_NAME, i18n.t("Could not save to Keychain."),
            )

    def open_preferences(self) -> None:
        """Show the preferences dialog / 打开偏好设置对话框."""
        dlg = PreferencesDialog(
            self._config_manager, self._credential_store, parent=self,
        )
        prev = self._config_manager.config
        prev_language = prev.ui_language
        prev_font = prev.ui_font_size
        prev_opacity = prev.window_opacity
        prev_toolbar_pad = prev.ui_toolbar_padding
        if dlg.exec() == PreferencesDialog.DialogCode.Accepted:
            cfg = self._config_manager.config
            self._view.setZoomFactor(cfg.zoom_factor)
            if (
                cfg.ui_font_size != prev_font
                or cfg.ui_toolbar_padding != prev_toolbar_pad
            ):
                app = QApplication.instance()
                if isinstance(app, QApplication):
                    apply_modern_style(
                        app,
                        base_pt=cfg.ui_font_size,
                        toolbar_pad_y=cfg.ui_toolbar_padding,
                    )
            if cfg.window_opacity != prev_opacity and (
                self._downloads_panel is not None
            ):
                self._downloads_panel.setWindowOpacity(
                    cfg.window_opacity / 100.0,
                )
            if cfg.ui_language != prev_language:
                # Flip the active language first so any retranslate()
                # callbacks below see the new value.
                # 先切换当前语言，后面的 retranslate() 才能看到新值。
                i18n.set_language(cfg.ui_language)
                self.retranslate()
                if self._downloads_panel is not None:
                    self._downloads_panel.retranslate()
                if self._on_language_changed is not None:
                    self._on_language_changed()
                # Rewrite the current page's host so the user lands on
                # the matching Overleaf mirror (cn ↔ www). Login cookies
                # are per-domain, so a re-login on the other mirror is
                # expected.
                # 切换语言时把当前地址换到对应镜像（cn ↔ www）。登录
                # cookie 按域名隔离，换站后通常需要重新登录。
                target = localized_url(
                    self._view.url().toString(), cfg.ui_language,
                )
                self._view.load(QUrl(target))

    def retranslate(self) -> None:
        """Re-apply translations to this window's toolbar and status.

        重新翻译本窗口的工具栏与状态栏文案。
        """
        for action, label_key, tooltip_key in self._toolbar_actions:
            action.setText(i18n.t(label_key))
            action.setToolTip(i18n.t(tooltip_key))

    # --------------------------------------------------------------- Qt hooks
    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Hide (don't quit) when the red button is clicked.

        点击红色关闭按钮时隐藏窗口但不退出应用（像 Claude Desktop）。
        Cmd+Q 仍会真正退出，因为走的是 ``app.quit()`` 而非 closeEvent。

        The app keeps running in the background; clicking the Dock icon
        re-shows the window via the activation hook in
        :mod:`overleaf_client.app`. Child ``window.open`` popups opt out
        by passing ``hide_on_close=False`` so they close normally.
        """
        if self._hide_on_close:
            event.ignore()
            self.hide()
            return
        event.accept()
