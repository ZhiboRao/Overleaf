"""Preferences dialog.

偏好设置对话框。
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
    QHBoxLayout,
    QLineEdit,
    QPushButton,
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
        self.setMinimumWidth(480)
        self._config_manager = config_manager
        self._credential_store = credential_store

        cfg = config_manager.config

        self._home_url = QLineEdit(cfg.home_url)
        self._zoom = QDoubleSpinBox()
        self._zoom.setRange(0.5, 3.0)
        self._zoom.setSingleStep(0.1)
        self._zoom.setDecimals(2)
        self._zoom.setValue(cfg.zoom_factor)

        # (user-data, display label). Order is what the user sees.
        # (内部值, 显示名)。顺序即下拉菜单顺序。
        self._language_choices: list[tuple[str, str]] = [
            ("auto", "Auto / 跟随系统"),
            ("en", "English"),
            ("zh", "中文"),
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
            "Offer to save credentials in Keychain / 提示将凭据保存至钥匙串",
        )
        self._autosave_creds.setChecked(cfg.autosave_credentials)

        self._download_dir = QLineEdit(cfg.download_dir or "")
        self._download_dir.setPlaceholderText(str(Path.home() / "Downloads"))
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._pick_download_dir)
        dir_row = QHBoxLayout()
        dir_row.addWidget(self._download_dir, 1)
        dir_row.addWidget(browse)

        clear_creds = QPushButton("Clear saved credentials / 清除已保存凭据")
        clear_creds.clicked.connect(self._clear_credentials)

        form = QFormLayout()
        form.addRow("Home URL / 首页地址:", self._home_url)
        form.addRow("Zoom factor / 缩放比例:", self._zoom)
        form.addRow("Language / 界面语言:", self._language)
        form.addRow(self._notifications)
        form.addRow(self._dock_badge)
        form.addRow(self._autosave_creds)
        form.addRow("Download dir / 下载目录:", dir_row)
        form.addRow(clear_creds)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
        )
        buttons.accepted.connect(self._apply_and_close)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons, alignment=Qt.AlignmentFlag.AlignRight)

    def _pick_download_dir(self) -> None:
        initial = self._download_dir.text() or str(Path.home() / "Downloads")
        chosen = QFileDialog.getExistingDirectory(
            self, "Choose download directory / 选择下载目录", initial,
        )
        if chosen:
            self._download_dir.setText(chosen)

    def _clear_credentials(self) -> None:
        self._credential_store.delete()

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
        )
        self.accept()
