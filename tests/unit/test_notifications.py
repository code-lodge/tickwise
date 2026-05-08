"""Unit tests for tickwise.platform.notifications."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from tickwise.platform import notifications as mod


@pytest.mark.unit
class TestNotifyDispatch:
    def test_uses_plyer_when_available(self) -> None:
        with patch.object(mod, "_notify_via_plyer", return_value=True) as plyer:
            assert mod.notify("Title", "Body") is True
            plyer.assert_called_once()

    def test_falls_through_to_osascript_on_macos(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "darwin")
        with (
            patch.object(mod, "_notify_via_plyer", return_value=False),
            patch.object(mod, "_notify_via_osascript", return_value=True) as osa,
        ):
            assert mod.notify("T", "B") is True
            osa.assert_called_once_with("T", "B")

    def test_falls_through_to_notify_send_on_linux(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "linux")
        with (
            patch.object(mod, "_notify_via_plyer", return_value=False),
            patch.object(mod, "_notify_via_notify_send", return_value=True) as ns,
        ):
            assert mod.notify("T", "B") is True
            ns.assert_called_once()

    def test_returns_false_when_no_backend_handles(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "win32")
        with patch.object(mod, "_notify_via_plyer", return_value=False):
            assert mod.notify("T", "B") is False


@pytest.mark.unit
class TestNotifyBackends:
    def test_notify_send_uses_app_name_and_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        runner = MagicMock()
        monkeypatch.setattr(mod.shutil, "which", lambda _: "/usr/bin/notify-send")
        monkeypatch.setattr(mod.subprocess, "run", runner)
        assert mod._notify_via_notify_send("T", "B", 7, "App") is True
        argv = runner.call_args.args[0]
        assert argv[0] == "notify-send"
        assert "-a" in argv and "App" in argv
        assert "-t" in argv and "7000" in argv
        assert argv[-2:] == ["T", "B"]

    def test_notify_send_skipped_without_binary(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(mod.shutil, "which", lambda _: None)
        assert mod._notify_via_notify_send("T", "B", 5, "App") is False

    def test_osascript_escapes_quotes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        runner = MagicMock()
        monkeypatch.setattr(mod.shutil, "which", lambda _: "/usr/bin/osascript")
        monkeypatch.setattr(mod.subprocess, "run", runner)
        assert mod._notify_via_osascript('Title "x"', 'Body "y"') is True
        script = runner.call_args.args[0][2]
        assert '\\"x\\"' in script and '\\"y\\"' in script

    def test_plyer_returns_false_on_import_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Force the lazy import of `plyer` to raise.
        import builtins

        real_import = builtins.__import__

        def _raise(name: str, *a: object, **kw: object) -> object:
            if name == "plyer":
                raise ImportError("no plyer")
            return real_import(name, *a, **kw)

        monkeypatch.setattr(builtins, "__import__", _raise)
        assert mod._notify_via_plyer("T", "B", 5, "App") is False
