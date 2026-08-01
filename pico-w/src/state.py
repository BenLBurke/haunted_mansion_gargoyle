# Tracks the gargoyle's view of the world and detects changes worth reacting to.
#
# Deliberately dependency-free (no machine/framebuf/network imports) so this
# file is byte-for-byte usable both on the Pico and under CPython in tests --
# no enum or dataclasses modules, which MicroPython doesn't ship.

OPEN_STATUSES = ("OPERATING", "DOWN", "REFURBISHMENT")

PHASE_OPEN = "OPEN"
PHASE_CLOSED = "CLOSED"
PHASE_UNKNOWN = "UNKNOWN"


class AttractionStatus:
    def __init__(self, status, wait_minutes):
        self.status = status
        self.wait_minutes = wait_minutes


class ParkHours:
    def __init__(self, opening_text, closing_text):
        # Pre-formatted local wall-clock strings (e.g. "9:00am"), not
        # datetimes -- see themeparks_api.py for why.
        self.opening_text = opening_text
        self.closing_text = closing_text


class Snapshot:
    def __init__(self, attraction, hours):
        self.attraction = attraction
        self.hours = hours

    @property
    def phase(self):
        if self.attraction.status in OPEN_STATUSES:
            return PHASE_OPEN
        if self.attraction.status == "CLOSED":
            return PHASE_CLOSED
        return PHASE_UNKNOWN


class Reactions:
    def __init__(self):
        self.wait_time_changed = False
        self.wait_time_increased = False
        self.wait_time_decreased = False
        self.park_just_opened = False
        self.park_just_closed = False

    @property
    def any(self):
        return self.wait_time_changed or self.park_just_opened or self.park_just_closed


class StateTracker:
    """Feed it snapshots; it tells you what changed since the last one."""

    def __init__(self):
        self._previous = None

    def update(self, snapshot):
        reactions = Reactions()
        prev = self._previous

        if prev is not None:
            prev_wait = prev.attraction.wait_minutes
            new_wait = snapshot.attraction.wait_minutes
            if prev_wait is not None and new_wait is not None and prev_wait != new_wait:
                reactions.wait_time_changed = True
                reactions.wait_time_increased = new_wait > prev_wait
                reactions.wait_time_decreased = new_wait < prev_wait

            if prev.phase != PHASE_OPEN and snapshot.phase == PHASE_OPEN:
                reactions.park_just_opened = True
            if prev.phase == PHASE_OPEN and snapshot.phase == PHASE_CLOSED:
                reactions.park_just_closed = True

        self._previous = snapshot
        return reactions

    @property
    def current(self):
        return self._previous
