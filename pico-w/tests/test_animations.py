import time

# Same MicroPython time.ticks_ms/ticks_diff/sleep_ms stub needed to import
# animations.py off-device -- see test_display.py for why.
if not hasattr(time, "ticks_ms"):
    time.ticks_ms = lambda: int(time.monotonic() * 1000)
    time.ticks_diff = lambda a, b: a - b
    time.ticks_add = lambda a, b: a + b
    time.sleep_ms = lambda ms: None

import animations
import scene


class FakeDevice:
    def __init__(self):
        self.calls = []

    def color565(self, r, g, b):
        return (r, g, b)

    def _record(self, name):
        def method(*args, **kwargs):
            self.calls.append((name, args, kwargs))

        return method

    def __getattr__(self, name):
        return self._record(name)


def _scene():
    s = scene.Scene(FakeDevice())
    s.draw_all()
    return s


def test_ghost_drift_eventually_completes_a_pass():
    s = _scene()
    ghost = animations.GhostDrift(s)
    ghost._next = 0  # due immediately
    ghost._x = -scene.GHOST_W
    steps = 0
    while ghost._x is not None and steps < 200:
        ghost._last = 0  # force each tick to be "due"
        ghost.tick()
        steps += 1
    assert ghost._x is None  # completed the pass and scheduled the next one
    assert steps < 200


def test_lightning_runs_without_error():
    s = _scene()
    animations.lightning(s, park_label="Disneyland")


def test_roll_in_calls_draw_digits_every_frame_with_shrinking_offset():
    s = _scene()
    offsets = []
    animations.roll_in(s, lambda y_offset: offsets.append(y_offset))
    assert len(offsets) == animations.ROLL_FRAMES
    assert offsets[0] > offsets[-1] == 0
