import random

from candle import MAX_BRIGHTNESS, MIN_BRIGHTNESS, next_flicker_value


def _rand01_from(rng):
    return rng.random


def test_flicker_value_stays_in_bounds():
    rng = random.Random(42)
    rand01 = _rand01_from(rng)
    value = 0.7
    for _ in range(2000):
        value = next_flicker_value(value, rand01)
        assert MIN_BRIGHTNESS <= value <= MAX_BRIGHTNESS


def test_flicker_is_deterministic_given_same_sequence():
    rng1 = random.Random(7)
    value = 0.5
    seq1 = []
    for _ in range(50):
        value = next_flicker_value(value, _rand01_from(rng1))
        seq1.append(value)

    rng2 = random.Random(7)
    value = 0.5
    seq2 = []
    for _ in range(50):
        value = next_flicker_value(value, _rand01_from(rng2))
        seq2.append(value)

    assert seq1 == seq2


def test_flicker_actually_varies():
    rng = random.Random(1)
    rand01 = _rand01_from(rng)
    value = 0.5
    values = set()
    for _ in range(100):
        value = next_flicker_value(value, rand01)
        values.add(round(value, 3))
    assert len(values) > 10
