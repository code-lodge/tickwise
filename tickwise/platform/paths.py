"""Platform-appropriate data and config directory resolution."""

import os
import sys
from pathlib import Path


def data_dir() -> Path:
    """Return the platform-appropriate directory for persistent data (SQLite DB, etc.).

    Returns:
        Absolute Path to the data directory (created if absent).

    Raises:
        RuntimeError: If the platform is not supported.
    """
    path = _resolve_data_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_dir() -> Path:
    """Return the platform-appropriate directory for configuration files.

    Returns:
        Absolute Path to the config directory (created if absent).

    Raises:
        RuntimeError: If the platform is not supported.
    """
    path = _resolve_config_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _resolve_data_dir() -> Path:
    platform = sys.platform
    if platform == "win32":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError("APPDATA environment variable is not set")
        return Path(appdata) / "Tickwise"
    if platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Tickwise"
    if platform.startswith("linux"):
        xdg_data = os.environ.get("XDG_DATA_HOME")
        linux_base: Path = Path(xdg_data) if xdg_data else Path.home() / ".local" / "share"
        return linux_base / "tickwise"
    raise RuntimeError(f"Unsupported platform: {platform}")


def _resolve_config_dir() -> Path:
    platform = sys.platform
    if platform == "win32":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError("APPDATA environment variable is not set")
        return Path(appdata) / "Tickwise"
    if platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Tickwise"
    if platform.startswith("linux"):
        xdg_cfg = os.environ.get("XDG_CONFIG_HOME")
        cfg_base: Path = Path(xdg_cfg) if xdg_cfg else Path.home() / ".config"
        return cfg_base / "tickwise"
    raise RuntimeError(f"Unsupported platform: {platform}")
