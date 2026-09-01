import time

import pytest

# animations.py (imported transitively via display.Screen) uses MicroPython's
# time.ticks_ms()/ticks_diff()/sleep_ms(), which CPython's time module
# doesn't have -- same stub tools/preview.py uses to make this importable
# off-device.
if not hasattr(time, "ticks_ms"):
    time.ticks_ms = lambda: int(time.monotonic() * 1000)
    time.ticks_diff = lambda a, b: a - b
    time.ticks_add = lambda a, b: a + b
    time.sleep_ms = lambda ms: None

import display


class FakeDevice:
    """Satisfies scene.Scene's needs (color565 + the fill_rectangle/
    fill_circle/draw_text8x8/draw_circle/clear primitives) without a real
    ILI9341 panel -- enough to construct a real Screen and check it
    delegates to scene/renderer/animations correctly."""

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


@pytest.fixture
def screen():
    return display.Screen(FakeDevice(), 320, 240, park_label="Disneyland")


def test_begin_clears_and_paints_the_static_scene(screen):
    screen.begin()
    names = [c[0] for c in screen.device.calls]
    assert "clear" in names
    # draw_all() + draw_park_label() both draw a lot of primitives -- just
    # confirm something beyond clear() actually happened.
    assert len(names) > 5


def test_tick_advances_flame_and_ghost_without_error(screen):
    screen.begin()
    screen.tick()  # shouldn't raise, even though nothing's due yet


def test_show_stale_then_clear_stale_round_trips(screen):
    screen.begin()
    before = len(screen.device.calls)
    screen.show_stale()
    assert len(screen.device.calls) > before

    before = len(screen.device.calls)
    screen.clear_stale()
    assert len(screen.device.calls) > before


class TestConsoleScreen:
    def test_begin_and_tick_are_silent_no_ops(self, capsys):
        from display import ConsoleScreen

        cs = ConsoleScreen()
        cs.begin()
        cs.tick()  # must not raise
        out = capsys.readouterr().out
        assert "mansion scene" in out

    def test_show_stale_and_clear_stale_print_something(self, capsys):
        from display import ConsoleScreen

        cs = ConsoleScreen()
        cs.show_stale()
        cs.clear_stale()
        out = capsys.readouterr().out
        assert "stale" in out.lower()
