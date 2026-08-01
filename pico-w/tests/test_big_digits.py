import big_digits


class FakeFB:
    def __init__(self):
        self.rects = []

    def rect(self, x, y, w, h, c, f=False):
        self.rects.append((x, y, w, h, c, f))


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
