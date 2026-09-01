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


def test_r_numeral_spans_the_full_tombstone_width():
    # A 2-digit number renders 96px wide (box_w=44, gap=8) -- R_NUMERAL used
    # to be only 84px wide, narrower than that, which silently broke
    # centering (nothing to center *within* once the content is wider than
    # the box). It should span the tombstone's actual full width (150px).
    x, y, w, h = scene.R_NUMERAL
    assert w == scene.TS_W
    assert x == scene.TS_X


def test_restore_handles_both_tombstone_and_sky_patches():
    s = scene.Scene(FakeDevice())
    s.draw_all()
    s.restore(scene.R_NUMERAL)  # inside the tombstone, overlaps the round dome
    s.restore((0, 100, 26, 33))  # a sky patch (roughly the ghost's rect)


def test_sky_patch_restore_matches_the_real_gradient_at_that_position():
    """The ghost's visible trailing line/flicker was restore() treating each
    erased patch as its own independent 0..1 gradient instead of sampling
    the real sky gradient at the patch's actual position. A patch restored
    near the bottom of the sky should come out close to SKY_BOTTOM, not
    SKY_MID (which is what a "restart at 0" gradient would produce)."""
    s = scene.Scene(FakeDevice())
    s._restore_sky_patch(0, 230, 26, 10)
    fills = [args for (name, args, _kw) in s.d.calls if name == "fill_rectangle"]
    assert fills
    last_color = fills[-1][-1]
    # rgb() on FakeDevice just returns the tuple unchanged
    dist_to_bottom = sum(abs(a - b) for a, b in zip(last_color, scene.SKY_BOTTOM))
    dist_to_mid = sum(abs(a - b) for a, b in zip(last_color, scene.SKY_MID))
    assert dist_to_bottom < dist_to_mid


def test_tombstone_patch_restore_leaves_corners_outside_the_dome_as_sky():
    """R_NUMERAL starts well up inside the round dome, not just the
    straight-sided body below it. A naive rectangular restore painted stone
    color into the corners outside the dome's curve too -- visible as a
    grey box around the numeral. The restored corner just inside a wide
    patch near the top of the dome should come out as sky, not stone."""
    s = scene.Scene(FakeDevice())
    # A row near the very top of the dome, spanning past the dome's edges.
    s._restore_tombstone_patch(scene.TS_X, scene.TS_Y + 2, scene.TS_W, 1)
    fills = [args for (name, args, _kw) in s.d.calls if name == "fill_rectangle"]
    # the leftmost fill on that row should be a sky color, not a stone color
    first_color = fills[0][-1]
    dist_to_sky = sum(abs(a - b) for a, b in zip(first_color, scene.SKY_TOP))
    dist_to_stone = sum(abs(a - b) for a, b in zip(first_color, scene.STONE_TOP))
    assert dist_to_sky < dist_to_stone
