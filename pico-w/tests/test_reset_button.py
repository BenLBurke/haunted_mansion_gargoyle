from reset_button import HoldDetector


def test_fires_once_when_hold_threshold_crossed():
    detector = HoldDetector(hold_ms=1000)

    assert detector.update(True, 0) is False
    assert detector.update(True, 500) is False
    assert detector.update(True, 999) is False
    assert detector.update(True, 1000) is True
    # Doesn't keep firing every tick while still held.
    assert detector.update(True, 1100) is False


def test_release_before_threshold_resets_the_timer():
    detector = HoldDetector(hold_ms=1000)

    assert detector.update(True, 0) is False
    assert detector.update(True, 500) is False
    assert detector.update(False, 600) is False  # released early
    assert detector.update(True, 700) is False  # press restarts the clock
    assert detector.update(True, 1699) is False
    assert detector.update(True, 1700) is True


def test_can_fire_again_after_a_release_and_new_hold():
    detector = HoldDetector(hold_ms=1000)

    assert detector.update(True, 0) is False
    assert detector.update(True, 1000) is True
    assert detector.update(False, 1100) is False
    assert detector.update(True, 1100) is False
    assert detector.update(True, 2100) is True


def test_never_pressed_never_fires():
    detector = HoldDetector(hold_ms=1000)
    for ms in range(0, 5000, 100):
        assert detector.update(False, ms) is False


def test_uses_injected_ticks_diff_for_wraparound_safety():
    calls = []

    def fake_ticks_diff(a, b):
        calls.append((a, b))
        return a - b

    detector = HoldDetector(hold_ms=1000, ticks_diff=fake_ticks_diff)
    detector.update(True, 0)
    detector.update(True, 1000)

    assert calls  # the injected function was actually used, not a hardcoded subtraction
