"""System-wide input idle detection on macOS.

macOS 全局输入空闲检测。

Returns the number of seconds since the user last touched the keyboard,
mouse, trackpad, or any HID input device — across the whole system, not
just this app. That makes it ideal for pausing a "work time" counter:
if the user walks away from the computer, idle time climbs; if they are
typing in a different app, idle time stays at zero (we cross-check with
window activation to decide whether *our* window counts as working).

返回系统级"上次输入到现在的秒数"。因为是系统级的，用户只要动了键鼠
它就归零；只有真的走开它才会增长，配合窗口激活状态即可判断是否真在
工作。

The implementation loads ``CoreGraphics`` via :mod:`ctypes` so we don't
need ``pyobjc-framework-Quartz``. On non-macOS platforms or if the
symbol is unavailable, :func:`seconds_since_last_input` returns ``0.0``
so callers can behave as if the user is always active.

通过 ctypes 直接调用 CoreGraphics 的 C 函数，避免新增 pyobjc-Quartz
依赖。在非 macOS 或符号缺失时返回 0.0（视作始终有活动）。
"""

from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import c_double, c_uint32

_LOGGER = logging.getLogger(__name__)


# Constants from <CoreGraphics/CGEventSource.h>.
# 常量来自 CoreGraphics/CGEventSource.h。
_HID_SYSTEM_STATE: int = 1        # kCGEventSourceStateHIDSystemState
_ANY_INPUT_EVENT_TYPE: int = 0xFFFFFFFF  # kCGAnyInputEventType (~0 as UInt32)


def _load_cg_symbol() -> "ctypes._NamedFuncPointer | None":
    """Return a bound ``CGEventSourceSecondsSinceLastEventType`` or None.

    返回绑定好的 C 函数指针；若平台不支持则返回 None。
    """
    if sys.platform != "darwin":
        return None
    try:
        framework = ctypes.CDLL(
            "/System/Library/Frameworks/ApplicationServices.framework"
            "/ApplicationServices",
        )
        fn = framework.CGEventSourceSecondsSinceLastEventType
    except (OSError, AttributeError) as exc:
        _LOGGER.info("CoreGraphics idle API unavailable (%s)", exc)
        return None
    fn.restype = c_double
    fn.argtypes = [c_uint32, c_uint32]
    return fn


_fn = _load_cg_symbol()


def seconds_since_last_input() -> float:
    """Seconds since the last keyboard / mouse / trackpad event.

    距离上次键鼠/触控板输入的秒数。

    Returns ``0.0`` on non-macOS or if the API fails — callers should
    treat that as "user is active" rather than special-casing it.
    非 macOS 或调用失败时返回 0.0，调用方按"有活动"处理即可。
    """
    if _fn is None:
        return 0.0
    try:
        return float(_fn(_HID_SYSTEM_STATE, _ANY_INPUT_EVENT_TYPE))
    except OSError as exc:
        _LOGGER.debug("CGEventSource call failed: %s", exc)
        return 0.0
