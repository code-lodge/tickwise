"""Unit tests for chronolens.classification.queue."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from chronolens.classification import queue as cq


def _job(idx: int) -> cq.ClassificationJob:
    return cq.ClassificationJob(
        activity_id=idx,
        captured_at=datetime.now(UTC),
        window_title=f"win-{idx}",
        process_name="proc",
        raw_ocr_text="",
        redacted_text="",
        phash="",
    )


@pytest.mark.unit
class TestClassificationQueue:
    def setup_method(self) -> None:
        cq.clear()

    def teardown_method(self) -> None:
        cq.clear()

    def test_submit_and_take(self) -> None:
        cq.submit(_job(1))
        assert cq.qsize() == 1
        taken = cq.take(timeout=0.1)
        assert taken is not None
        assert taken.activity_id == 1

    def test_take_timeout_returns_none(self) -> None:
        assert cq.take(timeout=0.05) is None

    def test_full_queue_drops_oldest(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import queue

        small: queue.Queue[cq.ClassificationJob] = queue.Queue(maxsize=2)
        monkeypatch.setattr(cq, "_q", small)

        cq.submit(_job(1))
        cq.submit(_job(2))
        cq.submit(_job(3))  # should drop #1

        ids = []
        while small.qsize():
            ids.append(small.get_nowait().activity_id)
        assert ids == [2, 3]

    def test_clear(self) -> None:
        cq.submit(_job(1))
        cq.submit(_job(2))
        cq.clear()
        assert cq.qsize() == 0
