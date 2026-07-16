# Drives a candlestick LED with a random-walk brightness pattern that reads
# as a flickering flame. next_flicker_value() is a pure function (no PWM or
# random-module imports) so it's testable under CPython without hardware --
# it takes a rand01 callable returning a float in [0, 1) instead of reaching
# for a global random module, since MicroPython's `random` isn't guaranteed
# to be seedable/reproducible the way CPython's is.

MIN_BRIGHTNESS = 0.15
MAX_BRIGHTNESS = 1.0
MAX_STEP = 0.22
GUTTER_CHANCE = 0.04


def next_flicker_value(current, rand01):
    if rand01() < GUTTER_CHANCE:
        return MIN_BRIGHTNESS
    delta = (rand01() * 2 - 1) * MAX_STEP
    value = current + delta
    if value < MIN_BRIGHTNESS:
        return MIN_BRIGHTNESS
    if value > MAX_BRIGHTNESS:
        return MAX_BRIGHTNESS
    return value


class Candle:
    def __init__(self, pwm, rand01):
        self._pwm = pwm
        self._rand01 = rand01
        self._brightness = 0.7

    def step(self):
        self._brightness = next_flicker_value(self._brightness, self._rand01)
        self._pwm.duty_u16(int(self._brightness * 65535))

    def off(self):
        self._pwm.duty_u16(0)


def make_candle(pin_number):
    import random

    from machine import PWM, Pin

    pwm = PWM(Pin(pin_number))
    pwm.freq(1000)
    return Candle(pwm, random.random)
