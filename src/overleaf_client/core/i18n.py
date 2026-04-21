"""UI string catalog and language selection.

界面文案字典与语言选择。

Strings are looked up by their English source text (gettext-style). The
module keeps the active language in process-global state so every widget
that formats a label via :func:`t` reflects the user's current choice
without plumbing the language through constructors.

文案以英文原文为键（gettext 风格）。当前语言以模块级全局状态保存，
任何通过 :func:`t` 取值的控件都会自动跟随用户选择，避免把语言参数
层层传递。
"""

from __future__ import annotations

import locale
import logging
from typing import Final

_LOGGER = logging.getLogger(__name__)


# Map from the canonical English source string to its Chinese translation.
# When the active language is "zh" and a key is missing from the map, the
# English source is returned as a safe fallback.
# 英文 → 中文的翻译表；若当前语言为 zh 而某键未登记，则回退到英文原文。
_ZH: Final[dict[str, str]] = {
    # ---- Application -------------------------------------------------
    "Loading…": "正在加载…",
    "Back online": "已恢复网络",
    "You appear to be offline": "网络已断开",
    "Page failed to load": "页面加载失败",
    "Unofficial macOS desktop client for Overleaf.":
        "Overleaf 的非官方 macOS 桌面客户端。",

    # ---- Toolbar -----------------------------------------------------
    "‹  Back": "‹  后退",
    "Forward  ›": "前进  ›",
    "⟳  Reload": "⟳  刷新",
    "⌂  Home": "⌂  首页",
    "⇣  Downloads": "⇣  下载",
    "Back": "后退",
    "Forward": "前进",
    "Reload": "刷新",
    "Home": "首页",
    "Downloads": "下载",

    # ---- Menu bar ----------------------------------------------------
    "About": "关于",
    "Preferences…": "偏好设置…",
    "Quit": "退出",
    "View": "视图",
    "Toggle Full Screen": "全屏切换",
    "Account": "账户",
    "Save Login to Keychain…": "保存登录到钥匙串…",

    # ---- Preferences: chrome -----------------------------------------
    "Preferences": "偏好设置",
    "General": "通用",
    "Appearance": "外观",
    "Notifications": "通知",
    "Credentials": "凭据",

    # ---- Preferences: General ----------------------------------------
    "Browser basics and appearance": "浏览器基础设置与外观",
    "NAVIGATION": "导航",
    "Home URL": "首页地址",
    "Language": "语言",
    "DISPLAY": "显示",
    "Zoom factor": "缩放比例",
    "Language switches both UI text and the Overleaf mirror "
    "(中文 → cn.overleaf.com, English → www.overleaf.com).":
        "语言选项同时切换界面文本和 Overleaf 镜像"
        "（中文 → cn.overleaf.com，English → www.overleaf.com）。",

    # ---- Preferences: Appearance -------------------------------------
    "Font size and window translucency": "字体大小与窗口透明度",
    "TYPOGRAPHY": "字体",
    "Base size": "基准字号",
    "LAYOUT": "布局",
    "Toolbar height": "工具栏高度",
    "TRANSLUCENCY": "透明度",
    "Window opacity": "窗口不透明度",
    "Opacity applies to Preferences and Downloads; "
    "the main browser window stays fully opaque for readability.":
        "透明度仅作用于偏好设置与下载面板；主浏览器窗口保持不透明"
        "以便阅读正文。",

    # ---- Preferences: Downloads --------------------------------------
    "Where files go when you save them": "下载保存位置",
    "LOCATION": "位置",
    "Download dir": "下载目录",
    "Browse…": "浏览…",
    "Choose download directory": "选择下载目录",
    "Leave empty to use the default ~/Downloads folder.":
        "留空则使用默认的 ~/Downloads 目录。",

    # ---- Preferences: Notifications ----------------------------------
    "System alerts and Dock feedback": "系统通知与 Dock 状态",
    "ALERTS": "提醒",
    "Enable system notifications": "启用系统通知",
    "Enable Dock badge": "启用 Dock 徽标",
    "Notifications use macOS Notification Center via osascript, "
    "falling back to the tray icon.":
        "通知通过 osascript 调用 macOS 通知中心，失败时回退到托盘通知。",

    # ---- Preferences: Credentials ------------------------------------
    "How saved logins are handled": "已保存登录的处理方式",
    "KEYCHAIN": "钥匙串",
    "Offer to save credentials in Keychain": "提示将凭据保存至钥匙串",
    "Clear saved credentials": "清除已保存凭据",
    "Credentials are stored in the macOS Keychain under service "
    "\"com.zhiborao.overleafclient\".":
        "凭据保存在 macOS 钥匙串中，服务名为 "
        "\"com.zhiborao.overleafclient\"。",

    # ---- Downloads panel ---------------------------------------------
    "Active and recent file transfers": "当前与最近的下载记录",
    "TRANSFERS": "传输列表",
    "No downloads yet": "暂无下载",
    "Clear completed": "清除已完成",
    "Close": "关闭",
    "Completed and cancelled items can be cleared at any time.":
        "已完成或已取消的条目可以随时清除。",

    # ---- Download card -----------------------------------------------
    "Starting…": "正在开始…",
    "Cancel": "取消",
    "Show": "显示",
    "Reveal in Finder": "在 Finder 中显示",
    "Completed": "已完成",
    "Cancelled": "已取消",
    "left": "剩余",
    "downloaded": "已下载",
    "Failed: {reason}": "已中断：{reason}",

    # ---- Login prompts -----------------------------------------------
    "Email (leave empty to skip):": "邮箱（留空则跳过）:",
    "Password:": "密码:",
    "Credentials saved to Keychain": "凭据已保存至钥匙串",
    "Could not save to Keychain.": "无法写入钥匙串。",
}


# One of "en" or "zh" — "auto" is resolved at set_language() time.
# 仅为 "en" 或 "zh"；"auto" 在 set_language() 内解析。
_current: str = "en"


def _detect_system_language() -> str:
    """Return ``"zh"`` if the OS locale looks Chinese, otherwise ``"en"``.

    根据系统 locale 返回 "zh" 或 "en"。
    """
    try:
        tag = (locale.getlocale()[0] or "") or (locale.getdefaultlocale()[0] or "")
    except (ValueError, TypeError) as exc:
        _LOGGER.debug("locale detection failed: %s", exc)
        tag = ""
    return "zh" if tag.lower().startswith("zh") else "en"


def set_language(choice: str) -> str:
    """Activate a language; ``"auto"`` resolves via system locale.

    激活语言；``"auto"`` 按系统 locale 解析。

    Args:
        choice: One of ``"auto"``, ``"en"``, ``"zh"``. Unknown values
            fall back to English.

    Returns:
        The resolved language actually in effect (``"en"`` or ``"zh"``).
    """
    global _current
    if choice == "auto":
        _current = _detect_system_language()
    elif choice in ("en", "zh"):
        _current = choice
    else:
        _current = "en"
    return _current


def current() -> str:
    """Return the active language code / 返回当前激活的语言代码."""
    return _current


def t(text: str) -> str:
    """Translate ``text`` into the active language.

    把 ``text`` 翻译成当前语言。

    When the active language is English, ``text`` is returned unchanged.
    For other languages, the catalog is consulted and the English source
    is used as a fallback for missing keys so new strings are never
    silently dropped.
    当语言为英文时原样返回；其他语言查表，缺失时回退到英文原文。
    """
    if _current == "zh":
        return _ZH.get(text, text)
    return text
