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


def test_draw_all_runs_without_error():
    s = scene.Scene(FakeDevice())
    s.draw_all()
    assert len(s.d.calls) > 20  # a lot of primitives make up the facade+tombstone


def test_facade_elements_stay_within_the_panel_bounds():
    """Regression guard for the original transcription bugs: several facade
    elements (chimney, towers, entry arch...) were positioned using the
    wrong `_fb()` argument and ended up overlapping or off-screen. Every
    fill_rectangle the facade draws should land inside the 320x240 panel."""
    s = scene.Scene(FakeDevice())
    s.draw_facade()
    for name, args, kwargs in s.d.calls:
        if name == "fill_rectangle":
            x, y, w, h, _color = args
            assert -1 <= x, (name, args)
            assert y >= 0, (name, args)
            assert x + w <= scene.W + 1, (name, args)
            assert y + h <= scene.H + 1, (name, args)


def test_candlestick_and_lit_window_do_not_overlap():
    """The candlestick and the lit lancet window used to sit on top of each
    other (a real transcription bug in the facade's y-offsets) -- their
    boxes should be disjoint."""
    cs_x, cs_y, cs_w, cs_h = scene.CS_X, scene.CS_Y, scene.CS_W, scene.CS_H
    # lit window: x=18, w=8, bottom=24, h=17 -> top = H - 24 - 17
    win_x, win_w = 18, 8
    win_y = scene.H - 24 - 17
    win_h = 17

    x_overlap = cs_x < win_x + win_w and win_x < cs_x + cs_w
    y_overlap = cs_y < win_y + win_h and win_y < cs_y + cs_h
    assert not (x_overlap and y_overlap)


def test_restore_handles_both_tombstone_and_sky_patches():
    s = scene.Scene(FakeDevice())
    s.draw_all()
    s.restore(scene.R_NUMERAL)  # inside the tombstone
    s.restore((0, 100, 26, 33))  # a sky/facade patch (roughly the ghost's rect)
