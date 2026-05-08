"""Windows implementation of idle-time detection via GetLastInputInfo."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_kernel32.GetTickCount.restype = wintypes.DWORD


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


_user32.GetLastInputInfo.argtypes = [ctypes.POINTER(_LASTINPUTINFO)]
_user32.GetLastInputInfo.restype = wintypes.BOOL


def get_idle_seconds() -> float:
    """Return the number of seconds since the last keyboard or mouse input.

    Returns 0.0 if the API call fails (extremely rare — typically only on
    sandboxed processes without window-station access).
    """
    info = _LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(_LASTINPUTINFO)
    if not _user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    millis = (int(_kernel32.GetTickCount()) - int(info.dwTime)) & 0xFFFFFFFF
    return millis / 1000.0
