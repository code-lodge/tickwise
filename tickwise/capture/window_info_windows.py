"""Windows implementation of window-info queries.

Uses ctypes against user32/kernel32/psapi to avoid the pywin32 dependency
during testing. The functions return empty/zero values silently if the API
is unavailable (e.g. running headless under WSL, or in CI without a session).
"""

from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes

from tickwise.capture.window_info import WindowInfo

logger = logging.getLogger(__name__)

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_psapi = ctypes.WinDLL("psapi", use_last_error=True)

_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
_user32.GetWindowTextLengthW.restype = ctypes.c_int
_user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.GetWindowTextW.restype = ctypes.c_int
_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


_user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(_RECT)]
_user32.GetWindowRect.restype = wintypes.BOOL

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_kernel32.OpenProcess.restype = wintypes.HANDLE
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL

_psapi.GetModuleBaseNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.HMODULE,
    wintypes.LPWSTR,
    wintypes.DWORD,
]
_psapi.GetModuleBaseNameW.restype = wintypes.DWORD


def _window_title(hwnd: int) -> str:
    length = _user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    _user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def _process_name(pid: int) -> str:
    handle = _kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(260)
        copied = _psapi.GetModuleBaseNameW(handle, None, buf, 260)
        return buf.value if copied else ""
    finally:
        _kernel32.CloseHandle(handle)


def get_active_window() -> WindowInfo:
    """Return the title, process name, and PID of the currently focused window.

    Returns an empty WindowInfo (title=process_name="", pid=None) when no
    foreground window is available — this is the case immediately after
    boot or on a locked workstation.
    """
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return WindowInfo(title="", process_name="", pid=None)
    title = _window_title(hwnd)
    pid = wintypes.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    pid_value = int(pid.value) or None
    proc = _process_name(pid_value) if pid_value else ""
    return WindowInfo(title=title, process_name=proc, pid=pid_value)


def get_window_center() -> tuple[int, int] | None:
    """Return (x, y) of the focused window's centre, in virtual-screen coords.

    Used by the multi-monitor router to decide which display the window
    is currently on. Returns None when no foreground window is available.
    """
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return None
    rect = _RECT()
    if not _user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return ((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
