"""Lightweight network reachability monitor.

轻量网络连通性探测。

Qt's :class:`QNetworkInformation` reports the OS view of reachability. We
augment that with a periodic HTTP HEAD to the configured home URL so we
also detect DNS/captive-portal failures that the OS doesn't flag.

Qt 的 :class:`QNetworkInformation` 只反映系统层的「是否有网」；但
DNS 故障、校园网强制门户等情况系统并不标记。我们叠加一个周期性
HTTP HEAD 请求，兜底探测这些场景。
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtNetwork import (
    QNetworkAccessManager,
    QNetworkReply,
    QNetworkRequest,
)

_LOGGER = logging.getLogger(__name__)

_DEFAULT_INTERVAL_MS = 30_000
_TIMEOUT_MS = 8_000


class NetworkMonitor(QObject):
    """Emit signals when connectivity to a target URL changes.

    当目标站点连通性变化时发送信号。

    Signals:
        online_changed: Emitted with the current online state (True/False)
            whenever the state flips.
    """

    online_changed = Signal(bool)

    def __init__(
        self,
        target_url: str,
        parent: QObject | None = None,
        poll_interval_ms: int = _DEFAULT_INTERVAL_MS,
    ) -> None:
        """Initialize the monitor.

        Args:
            target_url: HTTP(S) URL used for reachability probes.
            parent: Optional QObject parent.
            poll_interval_ms: Probe interval in milliseconds.
        """
        super().__init__(parent)
        self._target = QUrl(target_url)
        self._manager = QNetworkAccessManager(self)
        self._online: bool | None = None
        self._interval = poll_interval_ms
        self._timer_id: int = 0

    def start(self) -> None:
        """Begin periodic probing / 开始周期性探测."""
        if self._timer_id:
            return
        self._probe()
        self._timer_id = self.startTimer(self._interval)

    def stop(self) -> None:
        """Stop probing / 停止探测."""
        if self._timer_id:
            self.killTimer(self._timer_id)
            self._timer_id = 0

    def is_online(self) -> bool:
        """Return the last observed online state (default True).

        返回最近一次探测到的在线状态。
        """
        return bool(self._online) if self._online is not None else True

    # ------------------------------------------------------------------ Qt
    def timerEvent(self, _event: object) -> None:  # noqa: N802 - Qt override
        """Qt timer callback that triggers a probe.

        Qt 定时器回调，触发一次探测。
        """
        self._probe()

    # -------------------------------------------------------------- Internal
    def _probe(self) -> None:
        request = QNetworkRequest(self._target)
        request.setTransferTimeout(_TIMEOUT_MS)
        reply = self._manager.head(request)
        reply.finished.connect(lambda r=reply: self._on_reply(r))

    @Slot()
    def _on_reply(self, reply: QNetworkReply) -> None:
        online = reply.error() == QNetworkReply.NetworkError.NoError
        reply.deleteLater()
        if online != self._online:
            self._online = online
            _LOGGER.info("Network state changed: online=%s", online)
            self.online_changed.emit(online)
