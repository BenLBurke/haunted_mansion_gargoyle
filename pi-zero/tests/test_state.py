from gargoyle.state import ParkPhase, Snapshot, StateTracker
from gargoyle.themeparks_api import AttractionStatus


def snap(status: str, wait_minutes: int | None) -> Snapshot:
    return Snapshot(attraction=AttractionStatus(status=status, wait_minutes=wait_minutes, last_updated=None), hours=None)


def test_first_update_reports_no_reactions():
    tracker = StateTracker()
    reactions = tracker.update(snap("OPERATING", 20))
    assert reactions.any is False


def test_wait_time_increase_detected():
    tracker = StateTracker()
    tracker.update(snap("OPERATING", 20))
    reactions = tracker.update(snap("OPERATING", 35))
    assert reactions.wait_time_changed is True
    assert reactions.wait_time_increased is True
    assert reactions.wait_time_decreased is False


def test_wait_time_decrease_detected():
    tracker = StateTracker()
    tracker.update(snap("OPERATING", 35))
    reactions = tracker.update(snap("OPERATING", 10))
    assert reactions.wait_time_changed is True
    assert reactions.wait_time_decreased is True
    assert reactions.wait_time_increased is False


def test_unchanged_wait_time_reports_nothing():
    tracker = StateTracker()
    tracker.update(snap("OPERATING", 20))
    reactions = tracker.update(snap("OPERATING", 20))
    assert reactions.wait_time_changed is False


def test_park_open_to_close_transition():
    tracker = StateTracker()
    tracker.update(snap("OPERATING", 20))
    reactions = tracker.update(snap("CLOSED", None))
    assert reactions.park_just_closed is True
    assert reactions.park_just_opened is False


def test_park_close_to_open_transition():
    tracker = StateTracker()
    tracker.update(snap("CLOSED", None))
    reactions = tracker.update(snap("OPERATING", 20))
    assert reactions.park_just_opened is True
    assert reactions.park_just_closed is False


def test_down_status_counts_as_open_phase():
    assert snap("DOWN", None).phase == ParkPhase.OPEN


def test_unknown_status_is_unknown_phase():
    assert snap("SOME_NEW_STATUS", None).phase == ParkPhase.UNKNOWN
