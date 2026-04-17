"""Preferences dialog.

偏好设置对话框。

The layout follows iTerm2's preferences: a horizontal tab strip at the
top with underline indicator for the current page, and the page content
below. Each page hosts a tight form so related settings stay grouped.

布局参考 iTerm2：顶部横向 tab 条（选中项下方加蓝色下划线），下方是
当前页内容。每页只放一类相关设置，保持聚焦。
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from overleaf_client.core.config import ConfigManager
from overleaf_client.core.credentials import CredentialStore


class PreferencesDialog(QDialog):
    """Edit :class:`AppConfig` and stored credentials.

    编辑 :class:`AppConfig` 与已保存的凭据。
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        credential_store: CredentialStore,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the dialog.

        Args:
            config_manager: Source of current settings.
            credential_store: For viewing/clearing saved credentials.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Preferences / 偏好设置")
        self.setFixedSize(680, 600)
        self._config_manager = config_manager
        self._credential_store = credential_store

        cfg = config_manager.config
        # Start at the persisted opacity; live slider preview updates it.
        # 按保存的不透明度初始化；滑块拖动时实时预览。
        self.setWindowOpacity(cfg.window_opacity / 100.0)
        self._build_widgets(cfg)

        tabs = QTabWidget()
        tabs.setObjectName("PrefsTabs")
        tabs.setDocumentMode(True)
        tabs.tabBar().setObjectName("PrefsTabBar")
        tabs.tabBar().setExpanding(False)
        tabs.tabBar().setDrawBase(False)

        tabs.addTab(self._build_general_page(), "General / 通用")
        tabs.addTab(self._build_appearance_page(), "Appearance / 外观")
        tabs.addTab(self._build_downloads_page(), "Downloads / 下载")
        tabs.addTab(
            self._build_notifications_page(), "Notifications / 通知",
        )
        tabs.addTab(self._build_credentials_page(), "Credentials / 凭据")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
        )
        buttons.accepted.connect(self._apply_and_close)
        buttons.rejected.connect(self.reject)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(24, 14, 24, 20)
        button_row.addStretch(1)
        button_row.addWidget(buttons)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(tabs, 1)
        layout.addLayout(button_row)

    # -------------------------------------------------------------- Widgets
    def _build_widgets(self, cfg) -> None:
        self._home_url = QLineEdit(cfg.home_url)

        self._zoom = QDoubleSpinBox()
        self._zoom.setRange(0.5, 3.0)
        self._zoom.setSingleStep(0.1)
        self._zoom.setDecimals(2)
        self._zoom.setValue(cfg.zoom_factor)

        # The language choice also picks which Overleaf mirror to visit:
        #   zh → cn.overleaf.com (Chinese; usually faster in China)
        #   en → www.overleaf.com (English)
        #   auto → use Home URL unchanged (for self-hosted instances).
        # 语言选项同时决定访问哪个 Overleaf 镜像：zh → cn.overleaf.com；
        # en → www.overleaf.com；auto → 使用上方 Home URL（自建实例）。
        self._language_choices: list[tuple[str, str]] = [
            ("auto", "Auto (use Home URL) / 自动（按首页地址）"),
            ("en", "English — www.overleaf.com"),
            ("zh", "中文 — cn.overleaf.com"),
        ]
        self._language = QComboBox()
        for value, label in self._language_choices:
            self._language.addItem(label, value)
        current_idx = next(
            (i for i, (v, _) in enumerate(self._language_choices)
             if v == cfg.ui_language),
            0,
        )
        self._language.setCurrentIndex(current_idx)

        self._notifications = QCheckBox(
            "Enable system notifications / 启用系统通知",
        )
        self._notifications.setChecked(cfg.enable_notifications)

        self._dock_badge = QCheckBox(
            "Enable Dock badge / 启用 Dock 徽标",
        )
        self._dock_badge.setChecked(cfg.enable_dock_badge)

        self._autosave_creds = QCheckBox(
            "Offer to save credentials in Keychain / "
            "提示将凭据保存至钥匙串",
        )
        self._autosave_creds.setChecked(cfg.autosave_credentials)

        self._download_dir = QLineEdit(cfg.download_dir or "")
        self._download_dir.setPlaceholderText(
            str(Path.home() / "Downloads"),
        )

        self._font_size = QSpinBox()
        self._font_size.setRange(12, 24)
        self._font_size.setSingleStep(1)
        self._font_size.setSuffix(" pt")
        self._font_size.setValue(cfg.ui_font_size)

        self._toolbar_padding = QSpinBox()
        self._toolbar_padding.setRange(2, 14)
        self._toolbar_padding.setSingleStep(1)
        self._toolbar_padding.setSuffix(" px")
        self._toolbar_padding.setValue(cfg.ui_toolbar_padding)

        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        # Floor at 50% so the dialog can never become unreadable.
        # 下限 50%，防止窗口透得看不清。
        self._opacity_slider.setRange(50, 100)
        self._opacity_slider.setValue(cfg.window_opacity)
        self._opacity_value = QLabel(f"{cfg.window_opacity}%")
        self._opacity_value.setMinimumWidth(48)
        self._opacity_slider.valueChanged.connect(self._on_opacity_changed)

    # ---------------------------------------------------------------- Pages
    def _page_layout(self, page: QWidget) -> QVBoxLayout:
        layout = QVBoxLayout(page)
        layout.setContentsMargins(44, 32, 44, 28)
        layout.setSpacing(14)
        return layout

    def _new_form(self) -> QFormLayout:
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(14)
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow,
        )
        return form

    def _title(self, title: str, subtitle: str) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setContentsMargins(0, 0, 0, 6)
        box.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("PrefPageTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("PrefPageSubtitle")
        subtitle_label.setWordWrap(True)
        box.addWidget(title_label)
        box.addWidget(subtitle_label)
        return box

    def _section(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("PrefSectionLabel")
        return label

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setObjectName("PrefDivider")
        line.setFrameShape(QFrame.Shape.NoFrame)
        return line

    def _hint(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("PrefHintLabel")
        label.setWordWrap(True)
        return label

    def _build_general_page(self) -> QWidget:
        page = QWidget()
        layout = self._page_layout(page)

        layout.addLayout(self._title(
            "General / 通用",
            "Browser basics and appearance / 浏览器基础设置与外观",
        ))

        layout.addWidget(self._section("NAVIGATION / 导航"))
        nav_form = self._new_form()
        nav_form.addRow("Home URL / 首页地址", self._home_url)
        nav_form.addRow("Language / 语言", self._language)
        layout.addLayout(nav_form)

        layout.addWidget(self._section("DISPLAY / 显示"))
        display_form = self._new_form()
        display_form.addRow("Zoom factor / 缩放比例", self._zoom)
        layout.addLayout(display_form)

        layout.addWidget(self._divider())
        layout.addWidget(self._hint(
            "Language also switches the Overleaf deployment "
            "(中文 → cn, English → www).\n"
            "语言选项同时切换访问的 Overleaf 镜像。",
        ))
        layout.addStretch(1)
        return page

    def _build_appearance_page(self) -> QWidget:
        page = QWidget()
        layout = self._page_layout(page)

        layout.addLayout(self._title(
            "Appearance / 外观",
            "Font size and window translucency / 字体大小与窗口透明度",
        ))

        layout.addWidget(self._section("TYPOGRAPHY / 字体"))
        font_form = self._new_form()
        font_form.addRow("Base size / 基准字号", self._font_size)
        layout.addLayout(font_form)

        layout.addWidget(self._section("LAYOUT / 布局"))
        layout_form = self._new_form()
        layout_form.addRow(
            "Toolbar height / 工具栏高度", self._toolbar_padding,
        )
        layout.addLayout(layout_form)

        layout.addWidget(self._section("TRANSLUCENCY / 透明度"))
        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(12)
        opacity_row.addWidget(self._opacity_slider, 1)
        opacity_row.addWidget(self._opacity_value)
        opacity_form = self._new_form()
        opacity_form.addRow(
            "Window opacity / 窗口不透明度", opacity_row,
        )
        layout.addLayout(opacity_form)

        layout.addWidget(self._divider())
        layout.addWidget(self._hint(
            "Opacity applies to Preferences and Downloads; "
            "the main browser window stays fully opaque for readability.\n"
            "透明度仅作用于偏好设置与下载面板；主浏览器窗口保持不透明"
            "以便阅读正文。",
        ))
        layout.addStretch(1)
        return page

    def _build_downloads_page(self) -> QWidget:
        page = QWidget()
        layout = self._page_layout(page)

        layout.addLayout(self._title(
            "Downloads / 下载",
            "Where files go when you save them / "
            "下载保存位置",
        ))

        browse = QPushButton("Browse… / 浏览…")
        browse.clicked.connect(self._pick_download_dir)
        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        dir_row.addWidget(self._download_dir, 1)
        dir_row.addWidget(browse)

        layout.addWidget(self._section("LOCATION / 位置"))
        form = self._new_form()
        form.addRow("Download dir / 下载目录", dir_row)
        layout.addLayout(form)

        layout.addWidget(self._divider())
        layout.addWidget(self._hint(
            "Leave empty to use the default ~/Downloads folder.\n"
            "留空则使用默认的 ~/Downloads。",
        ))
        layout.addStretch(1)
        return page

    def _build_notifications_page(self) -> QWidget:
        page = QWidget()
        layout = self._page_layout(page)

        layout.addLayout(self._title(
            "Notifications / 通知",
            "System alerts and Dock feedback / 系统通知与 Dock 状态",
        ))

        layout.addWidget(self._section("ALERTS / 提醒"))
        layout.addWidget(self._notifications)
        layout.addWidget(self._dock_badge)

        layout.addWidget(self._divider())
        layout.addWidget(self._hint(
            "Notifications use macOS Notification Center via osascript, "
            "falling back to the tray icon.\n"
            "通知通过 osascript 调用 macOS 通知中心，失败回退到托盘通知。",
        ))
        layout.addStretch(1)
        return page

    def _build_credentials_page(self) -> QWidget:
        page = QWidget()
        layout = self._page_layout(page)

        layout.addLayout(self._title(
            "Credentials / 凭据",
            "How saved logins are handled / 已保存登录的处理方式",
        ))

        layout.addWidget(self._section("KEYCHAIN / 钥匙串"))
        layout.addWidget(self._autosave_creds)

        clear_creds = QPushButton(
            "Clear saved credentials / 清除已保存凭据",
        )
        clear_creds.clicked.connect(self._clear_credentials)
        clear_row = QHBoxLayout()
        clear_row.addWidget(clear_creds)
        clear_row.addStretch(1)
        layout.addLayout(clear_row)

        layout.addWidget(self._divider())
        layout.addWidget(self._hint(
            "Credentials are stored in the macOS Keychain under service "
            "\"com.zhiborao.overleafclient\".\n"
            "凭据保存在 macOS 钥匙串，服务名 "
            "\"com.zhiborao.overleafclient\"。",
        ))
        layout.addStretch(1)
        return page

    # ----------------------------------------------------------- Callbacks
    def _pick_download_dir(self) -> None:
        initial = self._download_dir.text() or str(
            Path.home() / "Downloads",
        )
        chosen = QFileDialog.getExistingDirectory(
            self, "Choose download directory / 选择下载目录", initial,
        )
        if chosen:
            self._download_dir.setText(chosen)

    def _clear_credentials(self) -> None:
        self._credential_store.delete()

    def _on_opacity_changed(self, value: int) -> None:
        self._opacity_value.setText(f"{value}%")
        self.setWindowOpacity(value / 100.0)

    def _apply_and_close(self) -> None:
        self._config_manager.update(
            home_url=self._home_url.text().strip() or (
                self._config_manager.config.home_url
            ),
            zoom_factor=float(self._zoom.value()),
            enable_notifications=self._notifications.isChecked(),
            enable_dock_badge=self._dock_badge.isChecked(),
            autosave_credentials=self._autosave_creds.isChecked(),
            download_dir=self._download_dir.text().strip() or None,
            ui_language=self._language.currentData() or "auto",
            ui_font_size=int(self._font_size.value()),
            window_opacity=int(self._opacity_slider.value()),
            ui_toolbar_padding=int(self._toolbar_padding.value()),
        )
        self.accept()
