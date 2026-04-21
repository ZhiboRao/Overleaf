"""Preferences dialog.

偏好设置对话框。

The layout follows iTerm2's preferences: a horizontal tab strip at the
top with an underline indicator for the current page, and the page
content below. Each page hosts a tight form so related settings stay
grouped. All user-visible strings go through :func:`i18n.t` so the
dialog follows the active UI language.

布局参考 iTerm2：顶部横向 tab 条（选中项下方加蓝色下划线），下方是
当前页内容。每页只放一类相关设置，保持聚焦。所有文案通过
:func:`i18n.t` 取值，跟随当前界面语言。
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

from overleaf_client.core import i18n
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
        self.setWindowTitle(i18n.t("Preferences"))
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

        tabs.addTab(self._build_general_page(), i18n.t("General"))
        tabs.addTab(self._build_appearance_page(), i18n.t("Appearance"))
        tabs.addTab(self._build_downloads_page(), i18n.t("Downloads"))
        tabs.addTab(self._build_notifications_page(), i18n.t("Notifications"))
        tabs.addTab(self._build_credentials_page(), i18n.t("Credentials"))

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

        # The language option drives BOTH UI text and which Overleaf mirror
        # we visit. Labels stay bilingual here so users who can't yet read
        # the current UI can still find the language they want.
        # 语言选项同时决定界面文本和 Overleaf 镜像；此处标签保持中英双语，
        # 以便看不懂当前语言的用户也能找到目标语言。
        self._language_choices: list[tuple[str, str]] = [
            ("auto", "Auto / 自动（跟随系统）"),
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
            i18n.t("Enable system notifications"),
        )
        self._notifications.setChecked(cfg.enable_notifications)

        self._dock_badge = QCheckBox(i18n.t("Enable Dock badge"))
        self._dock_badge.setChecked(cfg.enable_dock_badge)

        self._autosave_creds = QCheckBox(
            i18n.t("Offer to save credentials in Keychain"),
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
            i18n.t("General"),
            i18n.t("Browser basics and appearance"),
        ))

        layout.addWidget(self._section(i18n.t("NAVIGATION")))
        nav_form = self._new_form()
        nav_form.addRow(i18n.t("Home URL"), self._home_url)
        nav_form.addRow(i18n.t("Language"), self._language)
        layout.addLayout(nav_form)

        layout.addWidget(self._section(i18n.t("DISPLAY")))
        display_form = self._new_form()
        display_form.addRow(i18n.t("Zoom factor"), self._zoom)
        layout.addLayout(display_form)

        layout.addWidget(self._divider())
        layout.addWidget(self._hint(i18n.t(
            "Language switches both UI text and the Overleaf mirror "
            "(中文 → cn.overleaf.com, English → www.overleaf.com).",
        )))
        layout.addStretch(1)
        return page

    def _build_appearance_page(self) -> QWidget:
        page = QWidget()
        layout = self._page_layout(page)

        layout.addLayout(self._title(
            i18n.t("Appearance"),
            i18n.t("Font size and window translucency"),
        ))

        layout.addWidget(self._section(i18n.t("TYPOGRAPHY")))
        font_form = self._new_form()
        font_form.addRow(i18n.t("Base size"), self._font_size)
        layout.addLayout(font_form)

        layout.addWidget(self._section(i18n.t("LAYOUT")))
        layout_form = self._new_form()
        layout_form.addRow(i18n.t("Toolbar height"), self._toolbar_padding)
        layout.addLayout(layout_form)

        layout.addWidget(self._section(i18n.t("TRANSLUCENCY")))
        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(12)
        opacity_row.addWidget(self._opacity_slider, 1)
        opacity_row.addWidget(self._opacity_value)
        opacity_form = self._new_form()
        opacity_form.addRow(i18n.t("Window opacity"), opacity_row)
        layout.addLayout(opacity_form)

        layout.addWidget(self._divider())
        layout.addWidget(self._hint(i18n.t(
            "Opacity applies to Preferences and Downloads; "
            "the main browser window stays fully opaque for readability.",
        )))
        layout.addStretch(1)
        return page

    def _build_downloads_page(self) -> QWidget:
        page = QWidget()
        layout = self._page_layout(page)

        layout.addLayout(self._title(
            i18n.t("Downloads"),
            i18n.t("Where files go when you save them"),
        ))

        browse = QPushButton(i18n.t("Browse…"))
        browse.clicked.connect(self._pick_download_dir)
        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        dir_row.addWidget(self._download_dir, 1)
        dir_row.addWidget(browse)

        layout.addWidget(self._section(i18n.t("LOCATION")))
        form = self._new_form()
        form.addRow(i18n.t("Download dir"), dir_row)
        layout.addLayout(form)

        layout.addWidget(self._divider())
        layout.addWidget(self._hint(i18n.t(
            "Leave empty to use the default ~/Downloads folder.",
        )))
        layout.addStretch(1)
        return page

    def _build_notifications_page(self) -> QWidget:
        page = QWidget()
        layout = self._page_layout(page)

        layout.addLayout(self._title(
            i18n.t("Notifications"),
            i18n.t("System alerts and Dock feedback"),
        ))

        layout.addWidget(self._section(i18n.t("ALERTS")))
        layout.addWidget(self._notifications)
        layout.addWidget(self._dock_badge)

        layout.addWidget(self._divider())
        layout.addWidget(self._hint(i18n.t(
            "Notifications use macOS Notification Center via osascript, "
            "falling back to the tray icon.",
        )))
        layout.addStretch(1)
        return page

    def _build_credentials_page(self) -> QWidget:
        page = QWidget()
        layout = self._page_layout(page)

        layout.addLayout(self._title(
            i18n.t("Credentials"),
            i18n.t("How saved logins are handled"),
        ))

        layout.addWidget(self._section(i18n.t("KEYCHAIN")))
        layout.addWidget(self._autosave_creds)

        clear_creds = QPushButton(i18n.t("Clear saved credentials"))
        clear_creds.clicked.connect(self._clear_credentials)
        clear_row = QHBoxLayout()
        clear_row.addWidget(clear_creds)
        clear_row.addStretch(1)
        layout.addLayout(clear_row)

        layout.addWidget(self._divider())
        layout.addWidget(self._hint(i18n.t(
            "Credentials are stored in the macOS Keychain under service "
            "\"com.zhiborao.overleafclient\".",
        )))
        layout.addStretch(1)
        return page

    # ----------------------------------------------------------- Callbacks
    def _pick_download_dir(self) -> None:
        initial = self._download_dir.text() or str(
            Path.home() / "Downloads",
        )
        chosen = QFileDialog.getExistingDirectory(
            self, i18n.t("Choose download directory"), initial,
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
