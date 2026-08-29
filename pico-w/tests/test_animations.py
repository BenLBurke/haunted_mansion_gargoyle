import animations


class FakeFB:
    """Records every draw call by name/args -- doesn't need to actually
    render anything, just let us inspect what animations.py asked for."""

    def __init__(self):
        self.calls = []

    def _record(self, name):
        def method(*args, **kwargs):
            self.calls.append((name, args, kwargs))

        return method

    def __getattr__(self, name):
        return self._record(name)


def _first_call(fb, name):
    for call_name, args, kwargs in fb.calls:
        if call_name == name:
            return args
    raise AssertionError("fb.{}() was never called".format(name))


def test_play_runs_without_error_and_shows_every_frame():
    fb = FakeFB()
    shows = []
    sleeps = []

    animations.play(fb, 128, 64, lambda: shows.append(1), lambda ms: sleeps.append(ms), frame_count=5)

    assert len(shows) == 10  # 5 bat frames + 5 ghost frames
    assert sleeps == [animations.FRAME_DELAY_MS] * 10


def test_bat_size_matches_oled_baseline():
    fb = FakeFB()
    animations.play(fb, 128, 64, lambda: None, lambda ms: None, frame_count=3)

    # First ellipse call each bat frame is the body dot: (x, y, rx, ry, color, fill)
    x, y, rx, ry, color, fill = _first_call(fb, "ellipse")
    assert (rx, ry) == (3, 3)  # scale is 1.0 at the OLED's own 128x64 dimensions


def test_bat_size_scales_up_on_larger_canvas():
    fb = FakeFB()
    animations.play(fb, 320, 240, lambda: None, lambda ms: None, frame_count=3)

    x, y, rx, ry, color, fill = _first_call(fb, "ellipse")
    # scale = min(320/128, 240/64) = 2.5 -> int(3 * 2.5) == 7
    assert (rx, ry) == (7, 7)


def test_ghost_frame_skipped_while_too_small_to_draw():
    fb = FakeFB()
    animations._ghost_frame(fb, 64, 32, pulse=0.01, scale=1.0)
    assert fb.calls == []  # body_w/body_h round down below the drawable floor


def test_ghost_eyes_only_drawn_past_pulse_threshold():
    fb = FakeFB()
    animations._ghost_frame(fb, 64, 32, pulse=1.0, scale=1.0)
    eye_rects = [c for c in fb.calls if c[0] == "rect" and c[1][4] == 0]  # bg-colored rects
    assert len(eye_rects) == 2

    fb2 = FakeFB()
    # pulse=0.39 is big enough to clear the size floor (body drawn) but
    # still below the 0.4 eye threshold -- isolates "no eyes yet" from
    # "nothing drawn at all".
    animations._ghost_frame(fb2, 64, 32, pulse=0.39, scale=1.0)
    assert any(c[0] == "rect" for c in fb2.calls)  # torso did get drawn
    eye_rects2 = [c for c in fb2.calls if c[0] == "rect" and c[1][4] == 0]
    assert len(eye_rects2) == 0
