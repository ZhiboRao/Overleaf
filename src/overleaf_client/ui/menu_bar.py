"""Native macOS menu bar builder.

原生 macOS 菜单栏构造器。

Keeping menu construction separate from the window means any future
window type (preferences-only, secondary project window, etc.) can share
the same top-level menu without duplicating code. The function is also
safe to call again whenever the UI language changes — it calls
``menu_bar.clear()`` before rebuilding, so the caller can simply invoke
``build_menu_bar`` a second time to refresh every item's text.

将菜单构造与窗口实现解耦，便于未来的其他窗口（例如仅偏好设置窗口、
次级项目窗口）复用同一顶层菜单。语言切换后可再次调用本函数：函数
内部会先 ``menu_bar.clear()``，再按新语言重建所有项。
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMenuBar

from overleaf_client import APP_NAME
from overleaf_client.core import i18n


def _make_action(
    parent: QMenuBar, text: str, shortcut: QKeySequence | str | None,
    handler: Callable[[], None],
) -> QAction:
    action = QAction(text, parent)
    if shortcut is not None:
        action.setShortcut(
            shortcut if isinstance(shortcut, QKeySequence)
            else QKeySequence(shortcut),
        )
    action.triggered.connect(handler)
    return action


def build_menu_bar(
    menu_bar: QMenuBar,
    *,
    on_open_preferences: Callable[[], None],
    on_reload: Callable[[], None],
    on_toggle_fullscreen: Callable[[], None],
    on_save_credentials: Callable[[], None],
    on_about: Callable[[], None],
    on_quit: Callable[[], None],
) -> None:
    """Populate ``menu_bar`` with the application's top-level menus.

    将应用顶级菜单填充到 ``menu_bar``。

    Args:
        menu_bar: The :class:`QMenuBar` instance to populate (usually the
            shared menu bar when ``setMenuBar`` is not used on macOS).
        on_open_preferences: "Overleaf > Preferences…" handler.
        on_reload: "View > Reload" handler.
        on_toggle_fullscreen: "View > Enter Full Screen" handler.
        on_save_credentials: "Account > Save Login…" handler.
        on_about: "Help > About" handler.
        on_quit: "Overleaf > Quit" handler.
    """
    menu_bar.clear()

    # --- App menu (macOS auto-positions items labelled "Preferences"/"About"
    # / "Quit" into the canonical locations regardless of which menu they
    # live under). 显式菜单命名便于非 macOS 平台同样可见。
    app_menu = menu_bar.addMenu(APP_NAME)
    app_menu.addAction(_make_action(
        menu_bar, i18n.t("About"), None, on_about,
    ))
    app_menu.addSeparator()
    prefs = _make_action(
        menu_bar, i18n.t("Preferences…"),
        QKeySequence.StandardKey.Preferences, on_open_preferences,
    )
    prefs.setMenuRole(QAction.MenuRole.PreferencesRole)
    app_menu.addAction(prefs)
    app_menu.addSeparator()
    quit_act = _make_action(
        menu_bar, i18n.t("Quit"),
        QKeySequence.StandardKey.Quit, on_quit,
    )
    quit_act.setMenuRole(QAction.MenuRole.QuitRole)
    app_menu.addAction(quit_act)

    # --- View
    view_menu = menu_bar.addMenu(i18n.t("View"))
    view_menu.addAction(_make_action(
        menu_bar, i18n.t("Reload"),
        QKeySequence.StandardKey.Refresh, on_reload,
    ))
    view_menu.addAction(_make_action(
        menu_bar, i18n.t("Toggle Full Screen"),
        QKeySequence.StandardKey.FullScreen, on_toggle_fullscreen,
    ))

    # --- Account
    acc_menu = menu_bar.addMenu(i18n.t("Account"))
    acc_menu.addAction(_make_action(
        menu_bar, i18n.t("Save Login to Keychain…"),
        None, on_save_credentials,
    ))
