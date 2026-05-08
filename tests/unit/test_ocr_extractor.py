"""Unit tests for chronolens.ocr.extractor (without paddleocr installed)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from chronolens.capture.screenshot import Screenshot
from chronolens.ocr import extractor


@pytest.fixture(autouse=True)
def _reset_ocr() -> None:
    extractor.reset_for_test()


def _solid() -> Screenshot:
    return Screenshot(width=4, height=4, bgra=bytes([0, 0, 0, 255]) * 16)


@pytest.mark.unit
class TestExtractText:
    def test_returns_empty_when_paddle_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(extractor, "_get_ocr", lambda: None)
        assert extractor.extract_text(_solid()) == ""

    def test_concatenates_lines(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_ocr = MagicMock()
        fake_ocr.ocr.return_value = [
            [
                ([], ("hello", 0.99)),
                ([], ("world", 0.97)),
            ]
        ]
        monkeypatch.setattr(extractor, "_get_ocr", lambda: fake_ocr)
        assert extractor.extract_text(_solid()) == "hello world"

    def test_swallows_ocr_errors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_ocr = MagicMock()
        fake_ocr.ocr.side_effect = RuntimeError("boom")
        monkeypatch.setattr(extractor, "_get_ocr", lambda: fake_ocr)
        assert extractor.extract_text(_solid()) == ""

    def test_empty_ocr_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_ocr = MagicMock()
        fake_ocr.ocr.return_value = [None]
        monkeypatch.setattr(extractor, "_get_ocr", lambda: fake_ocr)
        assert extractor.extract_text(_solid()) == ""


@pytest.mark.unit
class TestGetOcrCaching:
    def test_caches_unavailable_state(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Force the lazy import to fail.
        import builtins

        real_import = builtins.__import__

        def _raise(name: str, *a: Any, **kw: Any) -> Any:
            if name == "paddleocr":
                raise ImportError("not installed")
            return real_import(name, *a, **kw)

        monkeypatch.setattr(builtins, "__import__", _raise)
        assert extractor._get_ocr() is None
        # Subsequent calls return the cached None without retrying the import.
        monkeypatch.setattr(builtins, "__import__", real_import)
        assert extractor._get_ocr() is None
