"""Unit tests for chronolens.platform.paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from chronolens.platform import paths


def _run_with_platform(platform: str, **env_overrides: str | None) -> tuple[Path, Path]:
    """Invoke data_dir() and config_dir() as if running on *platform*."""
    env = os.environ.copy()
    for k, v in env_overrides.items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v

    with patch.object(sys, "platform", platform), patch.dict(os.environ, env, clear=True):
        return paths._resolve_data_dir(), paths._resolve_config_dir()


@pytest.mark.unit
class TestWindowsPaths:
    def test_data_dir_uses_appdata(self) -> None:
        data, _ = _run_with_platform("win32", APPDATA="C:\\Users\\test\\AppData\\Roaming")
        assert data == Path("C:\\Users\\test\\AppData\\Roaming\\ChronoLens")

    def test_config_dir_same_as_data_on_windows(self) -> None:
        data, cfg = _run_with_platform("win32", APPDATA="C:\\Users\\test\\AppData\\Roaming")
        assert data == cfg

    def test_missing_appdata_raises(self) -> None:
        with pytest.raises(RuntimeError, match="APPDATA"):
            _run_with_platform("win32", APPDATA=None)


@pytest.mark.unit
class TestMacOSPaths:
    def test_data_dir_under_library(self) -> None:
        data, _ = _run_with_platform("darwin")
        assert data == Path.home() / "Library" / "Application Support" / "ChronoLens"

    def test_config_same_as_data_on_macos(self) -> None:
        data, cfg = _run_with_platform("darwin")
        assert data == cfg


@pytest.mark.unit
class TestLinuxPaths:
    def test_data_dir_default(self) -> None:
        data, _ = _run_with_platform("linux", XDG_DATA_HOME=None, XDG_CONFIG_HOME=None)
        assert data == Path.home() / ".local" / "share" / "chronolens"

    def test_data_dir_respects_xdg(self) -> None:
        data, _ = _run_with_platform("linux", XDG_DATA_HOME="/custom/data", XDG_CONFIG_HOME=None)
        assert data == Path("/custom/data/chronolens")

    def test_config_dir_default(self) -> None:
        _, cfg = _run_with_platform("linux", XDG_DATA_HOME=None, XDG_CONFIG_HOME=None)
        assert cfg == Path.home() / ".config" / "chronolens"

    def test_config_dir_respects_xdg(self) -> None:
        _, cfg = _run_with_platform("linux", XDG_DATA_HOME=None, XDG_CONFIG_HOME="/custom/cfg")
        assert cfg == Path("/custom/cfg/chronolens")


@pytest.mark.unit
def test_unsupported_platform_raises() -> None:
    with pytest.raises(RuntimeError, match="Unsupported platform"):
        _run_with_platform("freebsd")


@pytest.mark.unit
def test_data_dir_creates_directory(tmp_path: Path) -> None:
    expected = tmp_path / "new_dir" / "ChronoLens"
    with (
        patch.object(sys, "platform", "win32"),
        patch.dict(os.environ, {"APPDATA": str(tmp_path / "new_dir")}, clear=True),
    ):
        result = paths.data_dir()
    assert result == expected
    assert result.exists()
    assert result.is_dir()
