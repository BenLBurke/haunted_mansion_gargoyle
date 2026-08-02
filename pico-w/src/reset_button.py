# Hold a physical button for reset_hold_seconds to forget WiFi and reboot
# into setup mode -- which also lets you pick a different park, since the
# captive portal form already asks for that.
#
# HoldDetector is pure logic (no machine import) so it's testable under
# CPython; ResetButton is the thin hardware wrapper, following the same
# split used by candle.py (next_flicker_value vs. Candle).


def _default_diff(a, b):
    return a - b


class HoldDetector:
    def __init__(self, hold_ms=3000, ticks_diff=_default_diff):
        self._hold_ms = hold_ms
        self._ticks_diff = ticks_diff
        self._pressed_since = None

    def update(self, is_pressed, now_ms):
        """Feed this every tick. Returns True exactly once, the moment the
        hold threshold is crossed -- not True continuously while held."""
        if not is_pressed:
            self._pressed_since = None
            return False
        if self._pressed_since is None:
            self._pressed_since = now_ms
            return False
        if self._ticks_diff(now_ms, self._pressed_since) >= self._hold_ms:
            self._pressed_since = None
            return True
        return False


class ResetButton:
    def __init__(self, pin_number, hold_ms=3000):
        import time
        from machine import Pin

        self._pin = Pin(pin_number, Pin.IN, Pin.PULL_UP)
        self._time = time
        self._detector = HoldDetector(hold_ms, time.ticks_diff)

    def check(self):
        pressed = self._pin.value() == 0  # active-low: button ties the pin to GND
        return self._detector.update(pressed, self._time.ticks_ms())


def factory_reset():
    """Forgets saved WiFi credentials and resets the device into setup mode."""
    import machine

    from network_setup import forget_wifi

    print("reset button held -- forgetting WiFi and restarting into setup mode")
    forget_wifi()
    machine.reset()
