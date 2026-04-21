"""Downloads panel UI.

下载面板 UI。

Laid out like a Preferences page (title + subtitle, SECTION label, form
area, divider, hint, footer button row) so Preferences and Downloads
share the same chrome. Inside the SECTION the cards themselves still
follow Motrix's per-transfer design: file-type badge, filename + path,
thin progress bar, and a prominent percentage.

外层结构沿用偏好设置的"页"形式（大标题+副标题、分组标签、内容区、
分隔线、提示、底部按钮行），让两个窗口视觉一致。分组内部的每张下载
卡片仍参考 Motrix：文件类型徽标、文件名与路径、细进度条、大号百分比。
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from overleaf_client.core import i18n

_LOGGER = logging.getLogger(__name__)

# File extension → badge color. Anything not listed falls back to the
# default grey so the badge is never missing.
# 文件扩展名 → 徽标颜色；未列出的扩展名使用默认灰色兜底。
_BADGE_COLORS: dict[str, str] = {
    "pdf": "#e85a5a",
    "tex": "#0a84ff",
    "bib": "#34c759",
    "cls": "#34c759",
    "sty": "#34c759",
    "zip": "#e1a83f",
    "tar": "#e1a83f",
    "gz":  "#e1a83f",
    "png": "#af52de",
    "jpg": "#af52de",
    "jpeg": "#af52de",
    "gif": "#af52de",
    "svg": "#af52de",
    "txt": "#8e8e93",
    "log": "#8e8e93",
    "csv": "#34c759",
}
_BADGE_FALLBACK = "#8e8e93"


def _format_bytes(n: int) -> str:
    """Return ``n`` bytes as a human-readable string.

    将 ``n`` 字节格式化为易读字符串。
    """
    if n <= 0:
        return "0 B"
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(n)
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024
        idx += 1
    if idx == 0:
        return f"{int(value)} B"
    return f"{value:.1f} {units[idx]}"


def _format_duration(seconds: int) -> str:
    """Return a compact duration string like ``42s`` / ``3m 10s``.

    返回紧凑的时长字符串，例如 ``42s`` / ``3m 10s``。
    """
    if seconds <= 0:
        return "0s"
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    hours = seconds // 3600
    mins = (seconds % 3600) // 60
    return f"{hours}h {mins}m"


class FileTypeBadge(QLabel):
    """Colored square label that shows a file extension.

    以颜色方块展示文件扩展名的小标签。
    """

    def __init__(
        self, filename: str, parent: QWidget | None = None,
    ) -> None:
        """Initialize the badge from ``filename``'s extension."""
        super().__init__(parent)
        self.setObjectName("FileTypeBadge")
        ext = Path(filename).suffix.lower().lstrip(".") or "file"
        color = _BADGE_COLORS.get(ext, _BADGE_FALLBACK)
        shown = ext[:4].upper()
        self.setText(shown)
        self.setFixedSize(48, 48)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Inline because the color depends on the file type and isn't
        # known at stylesheet-compile time.
        # 使用内联样式，因颜色随文件类型变化，无法在静态样式表中预设。
        self.setStyleSheet(
            f"background: {color}; color: white; font-weight: 700; "
            "font-size: 11pt; border-radius: 10px;",
        )


class DownloadItemWidget(QWidget):
    """Row widget tracking a single :class:`QWebEngineDownloadRequest`.

    单个下载请求对应的卡片控件。
    """

    # Window for the rolling-average speed calculation; anything older is
    # dropped so the readout follows actual throughput fluctuations.
    # 计算滚动平均速度的窗口；更早的采样被丢弃，保证读数能反映真实变动。
    _SPEED_WINDOW_S = 5.0

    def __init__(
        self,
        download: QWebEngineDownloadRequest,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the card for ``download``.

        Args:
            download: The active download; signals on this object keep
                the UI in sync.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._download = download
        self._target_path = (
            Path(download.downloadDirectory()) / download.downloadFileName()
        )
        self._bytes_history: list[tuple[float, int]] = []

        self.setObjectName("DownloadCard")
        # Required so the QSS background / border actually paints on a bare
        # QWidget subclass (Qt skips styled bg otherwise).
        # 开启后 QSS 才会在 QWidget 子类上绘制背景/边框。
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._badge = FileTypeBadge(download.downloadFileName(), parent=self)

        self._name_label = QLabel(download.downloadFileName())
        self._name_label.setObjectName("DownloadCardName")
        self._name_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse,
        )
        self._name_label.setToolTip(str(self._target_path))

        self._path_label = QLabel(str(self._target_path.parent))
        self._path_label.setObjectName("DownloadCardPath")
        self._path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse,
        )

        self._percent_label = QLabel("0%")
        self._percent_label.setObjectName("DownloadCardPercent")
        self._percent_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)

        self._status_label = QLabel(i18n.t("Starting…"))
        self._status_label.setObjectName("DownloadCardStatus")

        self._cancel_button = QPushButton(i18n.t("Cancel"))
        self._cancel_button.setObjectName("DownloadCardAction")
        self._cancel_button.clicked.connect(self._on_cancel)

        self._reveal_button = QPushButton(i18n.t("Show"))
        self._reveal_button.setObjectName("DownloadCardAction")
        self._reveal_button.setToolTip(i18n.t("Reveal in Finder"))
        self._reveal_button.clicked.connect(self._on_reveal)
        self._reveal_button.hide()

        # -------- Top row: badge | name+path | percent --------
        name_box = QVBoxLayout()
        name_box.setContentsMargins(0, 0, 0, 0)
        name_box.setSpacing(2)
        name_box.addWidget(self._name_label)
        name_box.addWidget(self._path_label)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(14)
        top_row.addWidget(self._badge, 0, Qt.AlignmentFlag.AlignTop)
        top_row.addLayout(name_box, 1)
        top_row.addWidget(
            self._percent_label, 0, Qt.AlignmentFlag.AlignVCenter,
        )

        # -------- Bottom row: status | actions --------
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(10)
        bottom_row.addWidget(self._status_label, 1)
        bottom_row.addWidget(self._cancel_button)
        bottom_row.addWidget(self._reveal_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        layout.addLayout(top_row)
        layout.addWidget(self._progress)
        layout.addLayout(bottom_row)

        download.receivedBytesChanged.connect(self._refresh_progress)
        download.totalBytesChanged.connect(self._refresh_progress)
        download.stateChanged.connect(self._on_state_changed)
        download.isFinishedChanged.connect(self._refresh_progress)

        # Tick once a second to update speed / ETA even when Qt does not
        # emit receivedBytesChanged (e.g. very slow links).
        # 每秒触发一次，哪怕 receivedBytesChanged 不常发也能更新速度/ETA。
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._refresh_progress)
        self._tick_timer.start()

        self._refresh_progress()

    # ---------------------------------------------------------------- Status
    def _current_speed(self, now: float, received: int) -> float:
        self._bytes_history.append((now, received))
        cutoff = now - self._SPEED_WINDOW_S
        # Trim old samples but keep at least 2 so we can compute a delta.
        # 裁剪过旧采样，但保留至少 2 个以便计算差值。
        while len(self._bytes_history) > 2 and (
            self._bytes_history[0][0] < cutoff
        ):
            self._bytes_history.pop(0)
        if len(self._bytes_history) < 2:
            return 0.0
        t0, b0 = self._bytes_history[0]
        t1, b1 = self._bytes_history[-1]
        dt = t1 - t0
        if dt <= 0:
            return 0.0
        return max(0.0, (b1 - b0) / dt)

    @Slot()
    def _refresh_progress(self) -> None:
        now = time.monotonic()
        received = self._download.receivedBytes()
        total = self._download.totalBytes()
        speed = self._current_speed(now, received)

        if total > 0:
            pct = int(received * 100 / total)
            self._progress.setRange(0, 100)
            self._progress.setValue(pct)
            self._percent_label.setText(f"{pct}%")
            parts = [
                f"{_format_bytes(received)} / {_format_bytes(total)}",
                f"{_format_bytes(int(speed))}/s",
            ]
            remaining = total - received
            if speed > 0 and remaining > 0:
                parts.append(
                    f"{_format_duration(int(remaining / speed))} "
                    f"{i18n.t('left')}",
                )
            self._status_label.setText("  ·  ".join(parts))
        else:
            # Unknown total length → indeterminate (busy) progress bar.
            # 总长度未知 → 显示忙碌状态的无限循环进度条。
            self._progress.setRange(0, 0)
            self._percent_label.setText("—")
            parts = [
                f"{_format_bytes(received)} {i18n.t('downloaded')}",
                f"{_format_bytes(int(speed))}/s",
            ]
            self._status_label.setText("  ·  ".join(parts))

    @Slot()
    def _on_state_changed(self) -> None:
        state = self._download.state()
        states = QWebEngineDownloadRequest.DownloadState
        if state != states.DownloadInProgress:
            self._tick_timer.stop()
        if state == states.DownloadCompleted:
            self._progress.setRange(0, 100)
            self._progress.setValue(100)
            self._percent_label.setText("100%")
            size = _format_bytes(self._download.totalBytes())
            self._set_status(
                f"{i18n.t('Completed')} — {size}", flavor="ok",
            )
            self._cancel_button.hide()
            self._reveal_button.show()
        elif state == states.DownloadCancelled:
            self._progress.setRange(0, 100)
            self._progress.setValue(0)
            self._percent_label.setText("—")
            self._set_status(i18n.t("Cancelled"))
            self._cancel_button.hide()
        elif state == states.DownloadInterrupted:
            self._progress.setRange(0, 100)
            self._percent_label.setText("—")
            reason = self._download.interruptReasonString() or "interrupted"
            self._set_status(
                i18n.t("Failed: {reason}").format(reason=reason),
                flavor="error",
            )
            self._cancel_button.hide()

    def _set_status(self, text: str, *, flavor: str | None = None) -> None:
        self._status_label.setText(text)
        self._status_label.setProperty("state", flavor or "")
        # Force a style re-evaluation so the new property takes effect.
        # 强制重新计算样式，让新属性生效。
        style = self._status_label.style()
        style.unpolish(self._status_label)
        style.polish(self._status_label)

    def _on_cancel(self) -> None:
        self._download.cancel()

    def _on_reveal(self) -> None:
        # openUrl on the parent directory opens a Finder window; the file
        # itself isn't selected, but this is the simplest cross-process
        # behavior without shelling out to ``open -R``.
        # 用 openUrl 打开父目录；虽然不会选中文件，但这是无需外部进程的
        # 最简实现。
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(self._target_path.parent)),
        )

    def retranslate(self) -> None:
        """Re-apply translations to the static labels on this card.

        刷新卡片上静态文字（按钮、起始状态、工具提示）的翻译。

        Running transfer details (speed / bytes) repaint themselves on the
        next tick, so we only touch the labels that would otherwise stay
        frozen in the previous language.
        进度中的速度/字节数会在下一次 tick 自动重绘；这里只刷新那些
        否则会停留在旧语言的静态标签。
        """
        self._cancel_button.setText(i18n.t("Cancel"))
        self._reveal_button.setText(i18n.t("Show"))
        self._reveal_button.setToolTip(i18n.t("Reveal in Finder"))


class DownloadsPanel(QDialog):
    """Floating tool window listing all downloads for this session.

    列出当前会话所有下载的浮动工具窗口。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the panel (hidden until the first download)."""
        super().__init__(parent)
        self.setObjectName("DownloadsPanelRoot")
        self.setWindowTitle(i18n.t("Downloads"))
        # Plain non-modal QDialog (no Qt.Tool): on macOS the Tool flag
        # makes the window render as an NSPanel with a skinny utility
        # title bar, which visually shrinks the frame compared to
        # Preferences. A plain dialog gets the same chrome as
        # Preferences so the two windows match in size and weight.
        # 保持普通非模态 QDialog（不设 Qt.Tool）：Tool 标志在 macOS 上
        # 会让窗口按 NSPanel 渲染成纤细工具窗，整体比 Preferences 小
        # 一圈；去掉后两者窗框一致。
        self.setModal(False)
        # Opacity is driven by user preference; applied from the outside.
        # 不透明度由用户设置驱动，由外部在创建/保存时设置。
        self.setFixedSize(680, 600)

        # ---- Title + subtitle (same chrome as Preferences pages) ----
        self._title_label = QLabel(i18n.t("Downloads"))
        self._title_label.setObjectName("PrefPageTitle")
        self._subtitle_label = QLabel(
            i18n.t("Active and recent file transfers"),
        )
        self._subtitle_label.setObjectName("PrefPageSubtitle")
        self._subtitle_label.setWordWrap(True)

        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 6)
        title_box.setSpacing(2)
        title_box.addWidget(self._title_label)
        title_box.addWidget(self._subtitle_label)

        # ---- Section label above the list ----
        self._section_label = QLabel(i18n.t("TRANSFERS"))
        self._section_label.setObjectName("PrefSectionLabel")

        # ---- Scrollable list of download cards ----
        self._items_layout = QVBoxLayout()
        self._items_layout.setContentsMargins(0, 0, 0, 0)
        self._items_layout.setSpacing(12)
        self._items_layout.addStretch(1)

        container = QWidget()
        container.setLayout(self._items_layout)

        self._scroll = QScrollArea()
        self._scroll.setWidget(container)
        # ``WidgetResizable`` lets the inner column stretch to the viewport
        # width while still respecting the cards' own minimum sizes.
        # WidgetResizable 让内容宽度跟随 viewport，但卡片的最小宽度仍被
        # 尊重：超宽文件名会触发水平滚动条而不是被悄悄裁掉。
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )
        self._scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )

        # ---- Empty-state placeholder ----
        self._empty_icon = QLabel("⇣")
        self._empty_icon.setObjectName("DownloadsEmptyTitle")
        self._empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label = QLabel(i18n.t("No downloads yet"))
        self._empty_label.setObjectName("DownloadsEmptyLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._empty_container = QWidget()
        empty_box = QVBoxLayout(self._empty_container)
        empty_box.setContentsMargins(20, 30, 20, 30)
        empty_box.setSpacing(12)
        empty_box.addStretch(1)
        empty_box.addWidget(self._empty_icon)
        empty_box.addWidget(self._empty_label)
        empty_box.addStretch(2)

        # ---- Divider + hint (same as Preferences pages) ----
        self._divider = QFrame()
        self._divider.setObjectName("PrefDivider")
        self._divider.setFrameShape(QFrame.Shape.NoFrame)

        self._hint_label = QLabel(i18n.t(
            "Completed and cancelled items can be cleared at any time.",
        ))
        self._hint_label.setObjectName("PrefHintLabel")
        self._hint_label.setWordWrap(True)

        # ---- Page body stacks title → section → content → hint ----
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(44, 32, 44, 14)
        page_layout.setSpacing(14)
        page_layout.addLayout(title_box)
        page_layout.addWidget(self._section_label)
        page_layout.addWidget(self._empty_container, 1)
        page_layout.addWidget(self._scroll, 1)
        page_layout.addWidget(self._divider)
        page_layout.addWidget(self._hint_label)
        self._scroll.hide()

        # ---- Footer button row (aligns with Preferences Ok/Cancel row) ----
        self._clear_button = QPushButton(i18n.t("Clear completed"))
        self._clear_button.clicked.connect(self._clear_completed)
        self._close_button = QPushButton(i18n.t("Close"))
        self._close_button.setDefault(True)
        self._close_button.clicked.connect(self.hide)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(24, 14, 24, 20)
        button_row.addWidget(self._clear_button)
        button_row.addStretch(1)
        button_row.addWidget(self._close_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(page, 1)
        layout.addLayout(button_row)

        self._items: list[tuple[
            QWebEngineDownloadRequest, DownloadItemWidget,
        ]] = []

    @Slot(QWebEngineDownloadRequest)
    def track(self, download: QWebEngineDownloadRequest) -> None:
        """Create a card for ``download`` and bring the panel forward.

        为 ``download`` 创建一张卡片并把面板置前。
        """
        item = DownloadItemWidget(download, parent=self)
        self._items.append((download, item))
        # Insert at the top of the list (before the stretch spacer at -1).
        # 插入列表顶部（末尾 stretch 占位符之前）。
        self._items_layout.insertWidget(0, item)
        self._empty_container.hide()
        self._scroll.show()
        self.show()
        self.raise_()
        self.activateWindow()

    def _clear_completed(self) -> None:
        states = QWebEngineDownloadRequest.DownloadState
        remaining: list[tuple[
            QWebEngineDownloadRequest, DownloadItemWidget,
        ]] = []
        for dl, widget in self._items:
            if dl.state() in (
                states.DownloadCompleted,
                states.DownloadCancelled,
                states.DownloadInterrupted,
            ):
                self._items_layout.removeWidget(widget)
                widget.deleteLater()
            else:
                remaining.append((dl, widget))
        self._items = remaining
        if not self._items:
            self._scroll.hide()
            self._empty_container.show()

    def retranslate(self) -> None:
        """Re-apply translations to static labels / 刷新静态文案翻译."""
        self.setWindowTitle(i18n.t("Downloads"))
        self._title_label.setText(i18n.t("Downloads"))
        self._subtitle_label.setText(
            i18n.t("Active and recent file transfers"),
        )
        self._section_label.setText(i18n.t("TRANSFERS"))
        self._empty_label.setText(i18n.t("No downloads yet"))
        self._hint_label.setText(i18n.t(
            "Completed and cancelled items can be cleared at any time.",
        ))
        self._clear_button.setText(i18n.t("Clear completed"))
        self._close_button.setText(i18n.t("Close"))
        for _, widget in self._items:
            widget.retranslate()
