"""Unit tests for tickwise.capture.window_info_linux."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from tickwise.capture import window_info_linux as mod
from tickwise.capture.window_info import WindowInfo


@pytest.mark.unit
class TestSwayBackend:
    def test_returns_none_without_sock_or_swaymsg(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SWAYSOCK", raising=False)
        monkeypatch.delenv("I3SOCK", raising=False)
        with patch.object(mod.shutil, "which", return_value=None):
            assert mod._focused_from_sway() is None

    def test_walks_tree_for_focused_node(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SWAYSOCK", "/run/sway-sock")
        tree = {
            "name": "root",
            "focused": False,
            "nodes": [
                {
                    "name": "workspace",
                    "focused": False,
                    "nodes": [
                        {"name": "Editor", "focused": True, "pid": 4242},
                    ],
                }
            ],
        }
        completed = MagicMock(returncode=0, stdout=json.dumps(tree))
        with (
            patch.object(mod.shutil, "which", return_value="/usr/bin/swaymsg"),
            patch.object(mod.subprocess, "run", return_value=completed),
            patch.object(mod, "_process_name", return_value="codium"),
        ):
            info = mod._focused_from_sway()
        assert info == WindowInfo(title="Editor", process_name="codium", pid=4242)

    def test_returns_none_on_invalid_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SWAYSOCK", "/run/sway-sock")
        completed = MagicMock(returncode=0, stdout="not json")
        with (
            patch.object(mod.shutil, "which", return_value="/usr/bin/swaymsg"),
            patch.object(mod.subprocess, "run", return_value=completed),
        ):
            assert mod._focused_from_sway() is None


@pytest.mark.unit
class TestXdotoolBackend:
    def test_returns_none_without_xdotool(self) -> None:
        with patch.object(mod.shutil, "which", return_value=None):
            assert mod._focused_from_xdotool() is None

    def test_full_pipeline(self) -> None:
        wid = MagicMock(returncode=0, stdout="83886082\n")
        name = MagicMock(returncode=0, stdout="My Editor\n")
        pid = MagicMock(returncode=0, stdout="9001\n")
        with (
            patch.object(mod.shutil, "which", return_value="/usr/bin/xdotool"),
            patch.object(mod.subprocess, "run", side_effect=[wid, name, pid]),
            patch.object(mod, "_process_name", return_value="firefox"),
        ):
            info = mod._focused_from_xdotool()
        assert info == WindowInfo(title="My Editor", process_name="firefox", pid=9001)


@pytest.mark.unit
class TestDispatcher:
    def test_get_active_window_uses_first_successful_backend(self) -> None:
        sway_result = WindowInfo(title="A", process_name="p", pid=1)
        with (
            patch.object(mod, "_focused_from_sway", return_value=sway_result),
            patch.object(mod, "_focused_from_xdotool") as xd,
        ):
            assert mod.get_active_window() == sway_result
            xd.assert_not_called()

    def test_get_active_window_returns_empty_when_none_work(self) -> None:
        with (
            patch.object(mod, "_focused_from_sway", return_value=None),
            patch.object(mod, "_focused_from_xdotool", return_value=None),
        ):
            info = mod.get_active_window()
        assert info == WindowInfo(title="", process_name="", pid=None)

    def test_process_name_invalid_pid(self) -> None:
        assert mod._process_name(0) == ""
        assert mod._process_name(-1) == ""
