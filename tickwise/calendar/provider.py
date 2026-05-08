"""Abstract base for calendar providers + result types.

Each concrete provider (CalDAV, Google) inherits :class:`CalendarProvider`
and implements :meth:`push_sessions`. The sync service iterates over
active provider rows from the database, instantiates the right subclass,
and accumulates :class:`SyncReport` objects for the API to surface.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SyncReport:
    """Per-provider summary of one sync run."""

    provider_id: int
    provider_name: str
    events_pushed: int = 0
    events_updated: int = 0
    errors: list[str] = field(default_factory=list)


class CalendarProvider(ABC):
    """Concrete providers translate Tickwise sessions into calendar events."""

    type_name: str = "abstract"

    def __init__(self, provider_id: int, name: str, config: dict[str, Any]) -> None:
        self.provider_id = provider_id
        self.name = name
        self.config = config

    @abstractmethod
    def push_sessions(self, sessions: list[dict[str, Any]]) -> SyncReport:
        """Push or update calendar events for the given sessions.

        Implementations must catch their own transport errors and append a
        descriptive string to `report.errors` rather than raising — so a
        failure on one provider does not stop the sync loop.
        """
