import random

from gargoyle.leds.candle import MAX_BRIGHTNESS, MIN_BRIGHTNESS, next_flicker_value


def test_flicker_value_stays_in_bounds():
    rng = random.Random(42)
    value = 0.7
    for _ in range(2000):
        value = next_flicker_value(value, rng)
        assert MIN_BRIGHTNESS <= value <= MAX_BRIGHTNESS


def test_flicker_is_deterministic_given_same_seed():
    seq1 = []
    rng = random.Random(7)
    value = 0.5
    for _ in range(50):
        value = next_flicker_value(value, rng)
        seq1.append(value)

    seq2 = []
    rng = random.Random(7)
    value = 0.5
    for _ in range(50):
        value = next_flicker_value(value, rng)
        seq2.append(value)

    assert seq1 == seq2


def test_flicker_actually_varies():
    rng = random.Random(1)
    value = 0.5
    values = set()
    for _ in range(100):
        value = next_flicker_value(value, rng)
        values.add(round(value, 3))
    assert len(values) > 10
