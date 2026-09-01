# Screen controller for the 320x240 SPI TFT. Drop-in replacement for the
# SSD1306 version in pico-w/src/display.py -- the public interface is
# preserved (show_snapshot / show_message / play_wait_time_change_animation)
# with two additions, begin() and tick().
#
# Key departure from the OLED version: there is NO full framebuffer and no
# .show(). Draws go straight out over SPI. The static scene is painted once
# in begin(); after that only dirty rects are touched.

import animations_tft as animations
import renderer_tft as renderer
from scene import Scene


def make_display(spi_id, sck_pin, mosi_pin, cs_pin, dc_pin, rst_pin,
                 backlight_pin, width, height, rotation, baudrate=40_000_000):
    from machine import Pin, SPI
    from ili9341 import Display

    spi = SPI(spi_id, baudrate=baudrate, sck=Pin(sck_pin), mosi=Pin(mosi_pin))
    if backlight_pin is not None:
        Pin(backlight_pin, Pin.OUT).value(1)
    return Display(spi, cs=Pin(cs_pin), dc=Pin(dc_pin), rst=Pin(rst_pin),
                   width=width, height=height, rotation=rotation)


class Screen:
    def __init__(self, device, width, height, park_label=""):
        self.device = device
        self.width = width
        self.height = height
        self.park_label = park_label
        self.scene = Scene(device)
        self._flame = animations.FlameFlicker(self.scene)
        self._ghost = animations.GhostDrift(self.scene)
        self._last_wait = None
        self._msg_idx = 0

    def begin(self):
        """Paint the static scene once. Called from main.run() after construction."""
        self.device.clear()
        self.scene.draw_all()
        if self.park_label:
            self.scene.draw_park_label(self.park_label)

    def tick(self):
        """Cheap, non-blocking. Call every loop alongside candle.step()."""
        self._flame.tick()
        self._ghost.tick()

    def show_snapshot(self, snapshot, park_label, connected):
        # NOTE: no fill(0) -- the static scene stays put. Only the numeral or
        # message rect is repainted.
        renderer.render_snapshot(self.scene, snapshot, connected)

    def show_message(self, line1, line2=""):
        renderer.render_message(self.scene, line1, line2)

    def show_stale(self):
        """A fetch failed. Leave the numeral exactly where it is -- an always-on
        ambient display is more useful showing a stale wait than an error -- and
        draw a quiet in-fiction indicator instead. Deliberately NOT show_message(),
        which would wipe the tombstone."""
        renderer.render_stale_indicator(self.scene, True)

    def clear_stale(self):
        renderer.render_stale_indicator(self.scene, False)

    def play_wait_time_change_animation(self):
        """Lightning strike. Replaces the OLED build's 3.2s bat-then-ghost
        sting -- the ghost now drifts on its own ~150-210s schedule via tick()."""
        animations.lightning(self.scene, self.park_label)


class ConsoleScreen:
    """Unchanged in spirit from the SSD1306 build -- prints instead of drawing,
    so display_enabled: false still boots on a bare breadboard. begin()/tick()
    added to match the new Screen interface."""

    def begin(self):
        print("[screen] (static mansion scene would be painted here)")

    def tick(self):
        pass

    def show_snapshot(self, snapshot, park_label, connected):
        attraction = snapshot.attraction
        if attraction.status == "OPERATING" and attraction.wait_minutes is not None:
            status = "{} min wait".format(attraction.wait_minutes)
        else:
            status = attraction.status
        print("[screen] {}: {} (connected={})".format(park_label, status, connected))

    def show_message(self, line1, line2=""):
        print("[screen] {} {}".format(line1, line2).rstrip())

    def show_stale(self):
        print("[screen] (fetch failed -- keeping last known number, stale mark on)")

    def clear_stale(self):
        print("[screen] (stale mark off)")

    def play_wait_time_change_animation(self):
        print("[screen] (lightning strike would play here)")
