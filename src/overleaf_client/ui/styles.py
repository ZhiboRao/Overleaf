"""Global stylesheet applied to the whole application.

应用于整个应用的全局样式表。

The sheet is parameterized by a user-chosen base point size. All derived
sizes (page titles, section labels, download percentages, etc.) scale
relative to that base, so a user who prefers 18pt body text also gets
proportionally larger titles and smaller hints — no one element looks
out of place when the base changes.

样式表由用户配置的基准字号驱动：标题、分组标签、百分比等均按基准
同比缩放，改 base 时版式保持一致。

Colors reference Qt palette roles whenever possible so light / dark
modes render correctly.
颜色尽量引用 palette 角色，以兼容浅/深色模式。
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

_ACCENT = "#0a84ff"
_ACCENT_HOVER = "#0b74df"
_ACCENT_PRESSED = "#0959b0"


def _build_stylesheet(base_pt: int, toolbar_pad_y: int) -> str:
    """Return a QSS stylesheet scaled around ``base_pt``.

    以 ``base_pt`` 为基准生成同比缩放的 QSS 样式表。

    Args:
        base_pt: Base font point size; all derived sizes scale from it.
        toolbar_pad_y: Top/bottom padding (px) for main-window toolbar
            buttons (Back / Forward / Reload / Home / Downloads) — the
            knob that controls how thick the toolbar row feels.
    """
    scale = base_pt / 16.0

    def pt(n: float) -> int:
        return max(9, round(n * scale))

    # Fonts
    title_pt = pt(26)      # preferences page title
    subtitle_pt = pt(14)   # preferences page subtitle
    tab_pt = base_pt
    section_pt = pt(13)    # SECTION / 分组 label
    hint_pt = pt(13)
    status_pt = pt(13)     # QStatusBar
    card_name_pt = base_pt
    card_path_pt = pt(12)
    card_status_pt = pt(13)
    card_percent_pt = pt(22)
    badge_pt = pt(11)
    empty_title_pt = pt(44)
    empty_label_pt = pt(15)
    panel_header_pt = pt(22)
    panel_sub_pt = pt(13)

    return f"""
QMainWindow, QDialog, QWidget#DownloadsPanelRoot {{
    background: palette(window);
}}

QLabel {{
    background: transparent;
}}

/* -------------------------------------------------------------- Toolbar */
QToolBar {{
    background: palette(window);
    border: none;
    padding: 8px 12px;
    spacing: 4px;
}}

QToolBar::separator {{
    background: palette(mid);
    width: 1px;
    margin: 8px 6px;
}}

QToolBar QToolButton {{
    padding: {toolbar_pad_y}px 14px;
    border: 1px solid transparent;
    border-radius: 8px;
    color: palette(text);
    font-size: {base_pt}pt;
}}

QToolBar QToolButton:hover {{
    background: palette(light);
    border-color: palette(mid);
}}

QToolBar QToolButton:pressed {{
    background: palette(mid);
}}

QToolBar QToolButton:disabled {{
    color: palette(mid);
}}

/* ------------------------------------------------------------ Status bar */
QStatusBar {{
    background: palette(window);
    border-top: 1px solid palette(mid);
    color: palette(text);
    padding: 4px 12px;
    font-size: {status_pt}pt;
}}

QStatusBar::item {{
    border: none;
}}

QLabel#StatusClock, QLabel#StatusWork {{
    color: palette(text);
    padding: 0 10px;
    font-size: {status_pt}pt;
    font-family: "SF Mono", Menlo, Monaco, monospace;
}}

QLabel#StatusWork {{
    border-right: 1px solid palette(mid);
}}

/* ---------------------------------------------------------------- Buttons */
QPushButton {{
    padding: 7px 18px;
    border: 1px solid palette(mid);
    border-radius: 8px;
    background: palette(button);
    color: palette(button-text);
    min-height: 22px;
    font-size: {base_pt}pt;
}}

QPushButton:hover {{
    background: palette(light);
}}

QPushButton:pressed {{
    background: palette(mid);
}}

QPushButton:disabled {{
    color: palette(mid);
    background: palette(button);
}}

QPushButton:default {{
    background: {_ACCENT};
    color: white;
    border-color: {_ACCENT};
}}

QPushButton:default:hover {{
    background: {_ACCENT_HOVER};
    border-color: {_ACCENT_HOVER};
}}

QPushButton:default:pressed {{
    background: {_ACCENT_PRESSED};
    border-color: {_ACCENT_PRESSED};
}}

/* ----------------------------------------------------------------- Inputs */
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {{
    padding: 6px 10px;
    border: 1px solid palette(mid);
    border-radius: 8px;
    background: palette(base);
    selection-background-color: {_ACCENT};
    selection-color: white;
    min-height: 22px;
    font-size: {base_pt}pt;
}}

QLineEdit:focus, QDoubleSpinBox:focus,
QSpinBox:focus, QComboBox:focus {{
    border: 2px solid {_ACCENT};
    padding: 5px 9px;
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

/* --------------------------------------------------------------- Checkbox */
QCheckBox {{
    color: palette(text);
    spacing: 10px;
    padding: 4px 0;
    font-size: {base_pt}pt;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid palette(mid);
    border-radius: 5px;
    background: palette(base);
}}

QCheckBox::indicator:hover {{
    border-color: {_ACCENT};
}}

QCheckBox::indicator:checked {{
    background: {_ACCENT};
    border-color: {_ACCENT};
    image: none;
}}

/* ----------------------------------------------------------- Progress bar */
QProgressBar {{
    border: none;
    background: palette(mid);
    border-radius: 4px;
    min-height: 8px;
    max-height: 8px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    background: {_ACCENT};
    border-radius: 4px;
}}

/* --------------------------------------------------------------- Slider */
QSlider::groove:horizontal {{
    height: 4px;
    background: palette(mid);
    border-radius: 2px;
}}

QSlider::sub-page:horizontal {{
    background: {_ACCENT};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: white;
    border: 1px solid palette(mid);
    width: 18px;
    height: 18px;
    margin: -8px 0;
    border-radius: 9px;
}}

QSlider::handle:horizontal:hover {{
    border-color: {_ACCENT};
}}

/* ----------------------------------------------------------- Scroll areas */
QScrollArea {{
    background: transparent;
    border: none;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 12px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: palette(mid);
    min-height: 28px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical:hover {{
    background: palette(dark);
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: transparent;
    border: none;
    height: 0;
}}

/* ---------------------------------------------------------- Download card */
QWidget#DownloadCard {{
    background: palette(base);
    border: 1px solid palette(mid);
    border-radius: 12px;
}}

QLabel#DownloadCardName {{
    font-size: {card_name_pt}pt;
    font-weight: 600;
    color: palette(text);
}}

QLabel#DownloadCardPath {{
    font-size: {card_path_pt}pt;
    color: palette(dark);
}}

QLabel#DownloadCardPercent {{
    font-size: {card_percent_pt}pt;
    font-weight: 600;
    color: {_ACCENT};
    min-width: 90px;
}}

QLabel#DownloadCardStatus {{
    font-size: {card_status_pt}pt;
    color: palette(dark);
}}

QLabel#DownloadCardStatus[state="error"] {{
    color: #e85a5a;
}}

QLabel#DownloadCardStatus[state="ok"] {{
    color: #34c759;
}}

QLabel#FileTypeBadge {{
    font-size: {badge_pt}pt;
    font-weight: 700;
    color: white;
    border-radius: 10px;
}}

QPushButton#DownloadCardAction {{
    padding: 7px 18px;
    min-height: 24px;
    font-size: {base_pt}pt;
}}

/* --------------------------------------------------------- Downloads panel */
QLabel#DownloadsEmptyTitle {{
    color: palette(mid);
    font-size: {empty_title_pt}pt;
    font-weight: 300;
}}

QLabel#DownloadsEmptyLabel {{
    color: palette(dark);
    font-size: {empty_label_pt}pt;
}}

QLabel#DownloadsPanelHeader {{
    color: palette(text);
    font-size: {panel_header_pt}pt;
    font-weight: 600;
    padding: 16px 20px 6px 20px;
}}

QLabel#DownloadsPanelSubheader {{
    color: palette(dark);
    font-size: {panel_sub_pt}pt;
    padding: 0 20px 14px 20px;
}}

/* --------------------------------------------------------- iTerm-style tabs */
QTabWidget#PrefsTabs::pane {{
    border: none;
    border-top: 1px solid palette(mid);
    background: palette(window);
    top: -1px;
}}

QTabWidget#PrefsTabs > QTabBar {{
    qproperty-drawBase: 0;
    background: palette(window);
}}

QTabBar#PrefsTabBar {{
    alignment: center;
}}

QTabBar#PrefsTabBar::tab {{
    padding: 8px 22px;
    margin: 0;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: palette(text);
    font-size: {tab_pt}pt;
    min-width: 96px;
}}

QTabBar#PrefsTabBar::tab:selected {{
    color: {_ACCENT};
    border-bottom: 2px solid {_ACCENT};
    font-weight: 600;
}}

QTabBar#PrefsTabBar::tab:hover:!selected {{
    color: palette(dark);
}}

/* -------------------------------------------------------- Preferences */
QLabel#PrefPageTitle {{
    color: palette(text);
    font-size: {title_pt}pt;
    font-weight: 700;
    padding: 0;
}}

QLabel#PrefPageSubtitle {{
    color: palette(dark);
    font-size: {subtitle_pt}pt;
}}

QLabel#PrefSectionLabel {{
    color: {_ACCENT};
    font-size: {section_pt}pt;
    font-weight: 700;
    padding-top: 14px;
}}

QLabel#PrefHintLabel {{
    color: palette(dark);
    font-size: {hint_pt}pt;
    padding: 6px 0;
}}

QFrame#PrefDivider {{
    background: palette(mid);
    max-height: 1px;
    min-height: 1px;
    border: none;
}}

/* ----------------------------------------------------------- Find bar */
/* Chrome-style floating card overlaid on the top-right of the page. */
/* Chrome 风格的浮层卡片，覆盖在页面右上角。 */
QFrame#FindBar {{
    background: palette(base);
    border: 1px solid palette(mid);
    border-radius: 10px;
}}

QFrame#FindBar QLineEdit {{
    padding: 6px 10px;
    min-height: 24px;
    font-size: {base_pt}pt;
    border: 1px solid transparent;
    background: transparent;
}}

QFrame#FindBar QLineEdit:focus {{
    border: 1px solid {_ACCENT};
    background: palette(base);
}}

QPushButton#FindBarNav, QPushButton#FindBarClose {{
    padding: 4px 0;
    min-height: 28px;
    font-size: {base_pt}pt;
    border: 1px solid transparent;
    border-radius: 6px;
    background: transparent;
}}

QPushButton#FindBarNav:hover, QPushButton#FindBarClose:hover {{
    background: palette(light);
    border-color: palette(mid);
}}

QPushButton#FindBarClose {{
    color: palette(dark);
}}

QLabel#FindBarCount {{
    color: palette(dark);
    font-size: {hint_pt}pt;
    padding: 0 4px;
}}

QLabel#FindBarCount[state="error"] {{
    color: #e85a5a;
}}
"""


def apply_modern_style(
    app: QApplication, base_pt: int = 16, toolbar_pad_y: int = 4,
) -> None:
    """Install the app-wide stylesheet and default font.

    安装全局样式表和默认字号。

    Args:
        app: The running :class:`QApplication` instance.
        base_pt: Base font point size used as the scaling anchor.
        toolbar_pad_y: Top/bottom padding (px) for main-window
            toolbar buttons, controlling how tall the toolbar row is.
    """
    font = app.font()
    font.setPointSize(base_pt)
    font.setWeight(QFont.Weight.Normal)
    app.setFont(font)
    app.setStyleSheet(_build_stylesheet(base_pt, toolbar_pad_y))
