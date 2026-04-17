"""Cross-backend notification helper.

跨后端通知助手。

Order of preference:
    1. macOS native ``osascript`` (zero extra dependencies).
    2. Qt ``QSystemTrayIcon.showMessage`` fallback.

优先级：
    1. macOS 原生 ``osascript``（无需额外依赖）。
    2. Qt ``QSystemTrayIcon.showMessage`` 兜底。
"""

from __future__ import annotations

import logging
import shlex
import subprocess
import sys
from typing import Protocol

_LOGGER = logging.getLogger(__name__)


class _TrayLike(Protocol):
    """Subset of :class:`QSystemTrayIcon` used for fallback notifications."""

    def showMessage(  # noqa: N802 - Qt API
        self, title: str, message: str, *args: object,
    ) -> None: ...


class Notifier:
    """Display system notifications.

    显示系统通知。
    """

    def __init__(self, tray: _TrayLike | None = None) -> None:
        """Initialize the notifier.

        Args:
            tray: Optional tray icon used as a fallback backend.
        """
        self._tray = tray

    def notify(self, title: str, message: str) -> None:
        """Show a notification with the given title and message.

        弹出带标题与正文的通知。

        Args:
            title: Notification title.
            message: Notification body.
        """
        if sys.platform == "darwin" and self._notify_osascript(title, message):
            return
        if self._tray is not None:
            self._tray.showMessage(title, message)
            return
        _LOGGER.info("NOTIFY: %s | %s", title, message)

    @staticmethod
    def _notify_osascript(title: str, message: str) -> bool:
        script = (
            f'display notification {shlex.quote(message)} '
            f'with title {shlex.quote(title)}'
        )
        try:
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
                timeout=5,
            )
        except (
            FileNotFoundError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
        ) as exc:
            _LOGGER.debug("osascript notification failed: %s", exc)
            return False
        return True
