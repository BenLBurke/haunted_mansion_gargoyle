import big_digits


class FakeFB:
    """Matches the raw ILI9341 driver's primitive set (fill_rectangle/
    fill_circle), not framebuf -- this module draws straight to the panel,
    same as scene.py/renderer.py, no framebuf.FrameBuffer involved."""

    def __init__(self):
        self.rects = []
        self.circles = []

    def fill_rectangle(self, x, y, w, h, c):
        self.rects.append((x, y, w, h, c))

    def fill_circle(self, x, y, r, c):
        self.circles.append((x, y, r, c))


def test_measure_empty_string():
    assert big_digits.measure("") == 0


def test_measure_matches_box_and_gap_math():
    assert big_digits.measure("45", box_w=26, gap=6) == 26 * 2 + 6
    assert big_digits.measure("120", box_w=18, gap=4) == 18 * 3 + 4 * 2


def test_draw_number_draws_every_digit_without_error():
    fb = FakeFB()
    big_digits.draw_number(fb, 0, 0, "1234567890")
    assert len(fb.rects) > 0


def test_draw_number_ignores_non_digit_characters():
    fb = FakeFB()
    big_digits.draw_number(fb, 0, 0, "X")
    assert fb.rects == []
    assert fb.circles == []


def test_rounded_digits_get_corner_circles():
    # 0/3/6/8/9 have a curved bowl -- every corner two of its segments meet
    # at should get a rounding circle instead of a sharp right angle.
    for digit in "03689":
        fb = FakeFB()
        big_digits.draw_number(fb, 0, 0, digit)
        assert fb.circles, "expected rounded corners on digit {}".format(digit)


def test_non_rounded_digits_get_no_corner_circles():
    for digit in "1247":
        fb = FakeFB()
        big_digits.draw_number(fb, 0, 0, digit)
        assert fb.circles == [], "digit {} shouldn't have rounded corners".format(digit)


def test_horizontal_strokes_are_thinner_than_vertical_stems():
    # Per the design brief: vertical stems ~8px, horizontals ~6px at 66px
    # tall -- i.e. horizontal thickness should read as lighter than vertical.
    fb = FakeFB()
    big_digits.draw_number(fb, 0, 0, "8", box_w=44, box_h=66, thickness=8)
    heights = [h for (_, _, w, h, _) in fb.rects if w > h]  # wide-ish rects = horizontal strokes
    widths = [w for (_, _, w, h, _) in fb.rects if h > w]  # tall-ish rects = vertical strokes
    assert heights and widths
    assert max(heights) < max(widths)
