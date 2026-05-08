"""Unit tests for the autostart backends."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from chronolens.platform import autostart_linux, autostart_macos
from chronolens.platform.autostart import default_launch_command


@pytest.mark.unit
class TestDefaultLaunchCommand:
    def test_includes_python_and_module(self) -> None:
        cmd = default_launch_command()
        assert "-m chronolens" in cmd
        assert sys.executable in cmd or sys.executable.replace("\\", "/") in cmd


@pytest.mark.unit
class TestAutostartLinux:
    def test_enable_writes_desktop_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        autostart_linux.enable("/usr/bin/python -m chronolens")
        target = tmp_path / "autostart" / "chronolens.desktop"
        assert target.is_file()
        body = target.read_text("utf-8")
        assert "Exec=/usr/bin/python -m chronolens" in body
        assert "Type=Application" in body

    def test_is_enabled_reflects_file_presence(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        assert autostart_linux.is_enabled() is False
        autostart_linux.enable("cmd")
        assert autostart_linux.is_enabled() is True

    def test_disable_removes_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        autostart_linux.enable("cmd")
        autostart_linux.disable()
        assert autostart_linux.is_enabled() is False

    def test_disable_when_absent_is_noop(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        autostart_linux.disable()  # must not raise


@pytest.mark.unit
class TestAutostartMacOS:
    def test_enable_writes_plist(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", classmethod(lambda _cls: tmp_path))  # type: ignore[arg-type]
        autostart_macos.enable("/usr/bin/python -m chronolens")
        plist = tmp_path / "Library" / "LaunchAgents" / "com.chronolens.plist"
        assert plist.is_file()
        body = plist.read_bytes()
        assert b"com.chronolens" in body
        assert b"-m" in body
        assert b"chronolens" in body
        assert b"RunAtLoad" in body

    def test_is_enabled_and_disable(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", classmethod(lambda _cls: tmp_path))  # type: ignore[arg-type]
        assert autostart_macos.is_enabled() is False
        autostart_macos.enable("python -m chronolens")
        assert autostart_macos.is_enabled() is True
        autostart_macos.disable()
        assert autostart_macos.is_enabled() is False
        autostart_macos.disable()  # idempotent


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only registry path")
class TestAutostartWindows:
    def test_enable_disable_round_trip(self) -> None:
        from chronolens.platform import autostart_windows

        autostart_windows.disable()  # baseline
        try:
            assert autostart_windows.is_enabled() is False
            autostart_windows.enable("python.exe -m chronolens")
            assert autostart_windows.is_enabled() is True
        finally:
            autostart_windows.disable()
        assert autostart_windows.is_enabled() is False
