"""'Start with Windows' via the per-user Run registry key (no admin needed)."""

import sys

try:
    import winreg
except ImportError:
    winreg = None

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_NAME = "DesktopFoxy"


def supported() -> bool:
    # Only the packaged exe has a stable path worth registering.
    return winreg is not None and getattr(sys, "frozen", False)


def _command() -> str:
    return f'"{sys.executable}"'


def _current() -> str | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            return winreg.QueryValueEx(key, _NAME)[0]
    except OSError:
        return None


def is_enabled() -> bool:
    return supported() and _current() is not None


def set_enabled(enabled: bool) -> None:
    if not supported():
        return
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, _NAME, 0, winreg.REG_SZ, _command())
        else:
            try:
                winreg.DeleteValue(key, _NAME)
            except FileNotFoundError:
                pass


def refresh() -> None:
    """Point an existing entry at this exe, in case it was moved."""
    if is_enabled() and _current() != _command():
        set_enabled(True)
