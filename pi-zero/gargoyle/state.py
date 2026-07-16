"""Tracks the gargoyle's view of the world and detects changes worth reacting to."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from gargoyle.themeparks_api import AttractionStatus, ParkHours

OPEN_STATUSES = {"OPERATING", "DOWN", "REFURBISHMENT"}


class ParkPhase(Enum):
    OPEN = auto()
    CLOSED = auto()
    UNKNOWN = auto()


@dataclass
class Snapshot:
    attraction: AttractionStatus
    hours: ParkHours | None

    @property
    def phase(self) -> ParkPhase:
        if self.attraction.status in OPEN_STATUSES:
            return ParkPhase.OPEN
        if self.attraction.status == "CLOSED":
            return ParkPhase.CLOSED
        return ParkPhase.UNKNOWN


@dataclass
class Reactions:
    wait_time_changed: bool = False
    wait_time_increased: bool = False
    wait_time_decreased: bool = False
    park_just_opened: bool = False
    park_just_closed: bool = False

    @property
    def any(self) -> bool:
        return self.wait_time_changed or self.park_just_opened or self.park_just_closed


class StateTracker:
    """Feed it snapshots; it tells you what changed since the last one."""

    def __init__(self):
        self._previous: Snapshot | None = None

    def update(self, snapshot: Snapshot) -> Reactions:
        reactions = Reactions()
        prev = self._previous

        if prev is not None:
            prev_wait = prev.attraction.wait_minutes
            new_wait = snapshot.attraction.wait_minutes
            if prev_wait is not None and new_wait is not None and prev_wait != new_wait:
                reactions.wait_time_changed = True
                reactions.wait_time_increased = new_wait > prev_wait
                reactions.wait_time_decreased = new_wait < prev_wait

            if prev.phase != ParkPhase.OPEN and snapshot.phase == ParkPhase.OPEN:
                reactions.park_just_opened = True
            if prev.phase == ParkPhase.OPEN and snapshot.phase == ParkPhase.CLOSED:
                reactions.park_just_closed = True

        self._previous = snapshot
        return reactions

    @property
    def current(self) -> Snapshot | None:
        return self._previous
