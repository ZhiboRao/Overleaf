"""macOS Dock badge integration.

macOS Dock 图标徽标集成。

``pyobjc`` is imported lazily so the client remains installable on
non-macOS platforms (albeit as a no-op there).

延迟导入 ``pyobjc``，保证在非 macOS 平台上也可安装（仅退化为空操作）。
"""

from __future__ import annotations

import logging
import sys

_LOGGER = logging.getLogger(__name__)


class DockBadge:
    """Thin wrapper around ``NSApp.dockTile`` to set badge labels.

    基于 ``NSApp.dockTile`` 的徽标设置封装。
    """

    def __init__(self) -> None:
        """Initialize the badge helper (no-op off macOS)."""
        self._available = False
        self._dock_tile = None
        if sys.platform != "darwin":
            return
        try:
            # Imported here so the module still loads elsewhere.
            # 在此处导入以保证在其他系统也能加载模块。
            from AppKit import NSApplication  # type: ignore[import-untyped]
        except ImportError as exc:
            _LOGGER.info("pyobjc/AppKit unavailable (%s); Dock badge off.", exc)
            return
        self._dock_tile = NSApplication.sharedApplication().dockTile()
        self._available = True

    @property
    def available(self) -> bool:
        """Whether Dock badge updates will actually do something.

        是否有可用的 Dock 徽标后端。
        """
        return self._available

    def set_label(self, label: str | None) -> None:
        """Set or clear the Dock badge label.

        设置或清除 Dock 徽标文本。

        Args:
            label: Short label (e.g. "3" or "!"); pass ``None`` to clear.
        """
        if not self._available or self._dock_tile is None:
            return
        self._dock_tile.setBadgeLabel_(label or "")
