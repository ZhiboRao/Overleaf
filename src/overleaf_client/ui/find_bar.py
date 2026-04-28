"""In-page find bar for the embedded Overleaf web view.

页面查找栏（嵌入式 Overleaf 视图使用）。

Chrome / Safari 风格的查找条：输入框 + 上一个 / 下一个 + 匹配数 + 关闭。
按 ⌘F 唤起；Esc 关闭并清除高亮；回车查找下一个，Shift+回车查找上一个。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor, QKeyEvent
from PySide6.QtWebEngineCore import QWebEngineFindTextResult, QWebEnginePage
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from overleaf_client.core import i18n

if TYPE_CHECKING:
    from PySide6.QtWebEngineWidgets import QWebEngineView


class _FindLineEdit(QLineEdit):
    """QLineEdit that reports Escape and Shift+Enter as named signals.

    可上报 Esc / Shift+回车 的输入框（QLineEdit 子类）。

    QLineEdit 的默认行为：Escape 不触发任何动作，Enter 触发
    ``returnPressed``。但查找条需要 Esc 来关闭、Shift+回车来上翻，
    因此在此覆盖 :meth:`keyPressEvent` 暴露这两个事件。
    """

    escape_pressed = Signal()
    shift_return_pressed = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """Forward Esc / Shift+Enter as signals; defer the rest to Qt."""
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
            event.accept()
            return
        if (
            key in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self.shift_return_pressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class FindBar(QFrame):
    """Inline find-on-page bar bound to a :class:`QWebEngineView`.

    与 :class:`QWebEngineView` 绑定的页内查找栏。

    Layout: ``[ query ] [‹] [›] [count] [✕]``. Hidden by default; the
    main window calls :meth:`open` on ⌘F and :meth:`close_and_clear` on
    Esc.
    布局为 ``[查询框] [‹] [›] [匹配数] [✕]``，默认隐藏；主窗口在 ⌘F
    时调用 :meth:`open`，在 Esc 时调用 :meth:`close_and_clear`。
    """

    closed = Signal()

    def __init__(
        self,
        view: QWebEngineView,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the bar bound to ``view``.

        Args:
            view: The web view whose page receives ``findText`` calls.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._view = view
        self._last_query = ""
        # Cache the last (active, total) pair so retranslate() can redraw
        # the count label in the new language without re-querying.
        # 缓存上一次的匹配数，用于在切换语言时按新模板重绘。
        self._last_count: tuple[int, int] | None = None

        self.setObjectName("FindBar")
        self.setFrameShape(QFrame.Shape.NoFrame)
        # WA_StyledBackground lets QSS paint a background on this QFrame
        # subclass, so the bar visually separates from the web view.
        # 启用后 QSS 才能在该 QFrame 子类上绘制背景，与下方网页区分开。
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # Floating card sized like Chrome's find bar — wide enough for a
        # search query without dominating the page.
        # 浮层尺寸参考 Chrome：足以容纳查询，又不会占据过多页面。
        self.setFixedWidth(440)
        # Subtle drop shadow so the card lifts off the page beneath it.
        # 加柔和阴影，让卡片从下方页面浮起。
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 70))
        self.setGraphicsEffect(shadow)

        self._query = _FindLineEdit(self)
        self._query.setPlaceholderText(i18n.t("Find on page"))
        self._query.setClearButtonEnabled(True)
        self._query.textChanged.connect(self._on_text_changed)
        self._query.returnPressed.connect(self.find_next)
        self._query.shift_return_pressed.connect(self.find_previous)
        self._query.escape_pressed.connect(self.close_and_clear)

        self._prev_button = QPushButton("‹", self)
        self._prev_button.setObjectName("FindBarNav")
        self._prev_button.setToolTip(i18n.t("Find previous"))
        self._prev_button.setFixedWidth(32)
        self._prev_button.clicked.connect(self.find_previous)

        self._next_button = QPushButton("›", self)
        self._next_button.setObjectName("FindBarNav")
        self._next_button.setToolTip(i18n.t("Find next"))
        self._next_button.setFixedWidth(32)
        self._next_button.clicked.connect(self.find_next)

        self._count_label = QLabel("", self)
        self._count_label.setObjectName("FindBarCount")
        self._count_label.setMinimumWidth(70)
        self._count_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self._close_button = QPushButton("✕", self)
        self._close_button.setObjectName("FindBarClose")
        self._close_button.setToolTip(i18n.t("Close find bar"))
        self._close_button.setFixedWidth(32)
        self._close_button.clicked.connect(self.close_and_clear)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 10, 6)
        layout.setSpacing(6)
        layout.addWidget(self._query, 1)
        layout.addWidget(self._prev_button)
        layout.addWidget(self._next_button)
        layout.addWidget(self._count_label)
        layout.addWidget(self._close_button)

        # Match-count comes back via QWebEnginePage.findTextFinished.
        # 匹配数通过 findTextFinished 信号回传。
        page = self._view.page()
        if page is not None:
            page.findTextFinished.connect(self._on_find_finished)

        self.setVisible(False)

    # ------------------------------------------------------------- Public
    def open(self) -> None:
        """Show the bar and focus the input, pre-selecting any prior query.

        显示查找栏并聚焦输入框；若之前已有查询，则全选以便覆盖输入。
        """
        if not self.isVisible():
            self.setVisible(True)
        # raise_() each time so the overlay paints above the web view
        # even if some other child widget got promoted in between.
        # 每次置顶，确保浮层始终覆盖在网页视图之上。
        self.raise_()
        self._query.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self._query.selectAll()
        # If we already have a query, re-run search so highlights come
        # back without the user needing to retype.
        # 已有查询则重跑一次，无需用户重新输入即可恢复高亮。
        if self._query.text():
            self._run_find(self._query.text())

    @Slot()
    def close_and_clear(self) -> None:
        """Hide the bar and clear find highlights on the page.

        隐藏查找栏并清除页面上的查找高亮。
        """
        self.setVisible(False)
        page = self._view.page()
        if page is not None:
            # Empty string clears the current find session in QtWebEngine.
            # 传空字符串可清除当前查找会话与高亮。
            page.findText("")
        self._count_label.clear()
        self.closed.emit()

    @Slot()
    def find_next(self) -> None:
        """Jump to the next match (forward search).

        定位到下一个匹配项（向下查找）。
        """
        text = self._query.text()
        if not text:
            return
        self._run_find(text)

    @Slot()
    def find_previous(self) -> None:
        """Jump to the previous match (backward search).

        定位到上一个匹配项（向上查找）。
        """
        text = self._query.text()
        if not text:
            return
        self._run_find(text, backward=True)

    def retranslate(self) -> None:
        """Re-apply translations to static labels / 刷新静态文案翻译."""
        self._query.setPlaceholderText(i18n.t("Find on page"))
        self._prev_button.setToolTip(i18n.t("Find previous"))
        self._next_button.setToolTip(i18n.t("Find next"))
        self._close_button.setToolTip(i18n.t("Close find bar"))
        # The count label is rendered from an i18n template; refresh so
        # the units track the language switch.
        # 匹配数由模板渲染，刷新一次让单位词随语言切换。
        if self._last_count is not None:
            self._render_count(*self._last_count)

    # ------------------------------------------------------------ Internals
    @Slot(str)
    def _on_text_changed(self, text: str) -> None:
        if not text:
            # Empty input → clear highlights but keep the bar open so the
            # user can keep typing.
            # 输入清空时清除高亮但保留查找栏，方便继续输入。
            page = self._view.page()
            if page is not None:
                page.findText("")
            self._count_label.clear()
            self._last_count = None
            return
        self._run_find(text)

    def _run_find(self, text: str, *, backward: bool = False) -> None:
        page = self._view.page()
        if page is None:
            return
        flags = QWebEnginePage.FindFlag(0)
        if backward:
            flags |= QWebEnginePage.FindFlag.FindBackward
        self._last_query = text
        page.findText(text, flags)

    @Slot(QWebEngineFindTextResult)
    def _on_find_finished(self, result: QWebEngineFindTextResult) -> None:
        total = result.numberOfMatches()
        active = result.activeMatch()
        self._render_count(active, total)

    def _render_count(self, active: int, total: int) -> None:
        self._last_count = (active, total)
        if total <= 0:
            self._count_label.setText(i18n.t("No matches"))
            self._count_label.setProperty("state", "error")
        else:
            self._count_label.setText(
                i18n.t("{active}/{total}").format(
                    active=active, total=total,
                ),
            )
            self._count_label.setProperty("state", "")
        # Re-polish so the dynamic property change repaints.
        # 重新 polish 让属性变化触发重绘。
        style = self._count_label.style()
        style.unpolish(self._count_label)
        style.polish(self._count_label)

    # ------------------------------------------------------------- Qt hooks
    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """Close on Escape even when focus drifts off the input.

        即便焦点从输入框移开，按 Esc 仍能关闭查找栏。
        """
        if event.key() == Qt.Key.Key_Escape:
            self.close_and_clear()
            event.accept()
            return
        super().keyPressEvent(event)
