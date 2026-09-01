# Screen controller for the 320x240 SPI TFT gothic-mansion display.
#
# Key departure from the old SSD1306 build: there is NO full framebuffer and
# no .show(). A full RGB565 320x240 buffer would be 153,600 bytes -- more
# than half the Pico's 264KB of RAM, and won't fit alongside WiFi/TLS. So
# draws go straight out over SPI instead: the static scene is painted once
# in begin(), and after that only small dirty rects (the numeral, the
# on-screen candle flame, an occasional drifting ghost) are ever repainted.
# See scene.py for the geometry and the dirty-rect bookkeeping.

import animations
import renderer
from scene import Scene


def make_display(config):
    from machine import SPI, Pin
    from ili9341 import Display, color565

    spi = SPI(
        config["spi_id"],
        baudrate=config["spi_baudrate"],
        sck=Pin(config["spi_sck_pin"]),
        mosi=Pin(config["spi_mosi_pin"]),
        miso=Pin(config["spi_miso_pin"]),
    )
    backlight_pin = config.get("spi_backlight_pin")
    if backlight_pin is not None:
        Pin(backlight_pin, Pin.OUT).value(1)
    device = Display(
        spi,
        cs=Pin(config["spi_cs_pin"]),
        dc=Pin(config["spi_dc_pin"]),
        rst=Pin(config["spi_rst_pin"]),
        width=config["display_width"],
        height=config["display_height"],
        rotation=config["display_rotation"],
    )
    # ili9341.py exports color565() as a bare module function, not a Display
    # method -- scene.py calls it as `display.color565(...)` (so its own
    # tests can inject a fake device without importing the real driver), so
    # bind it onto the instance here to satisfy that.
    device.color565 = color565
    return device


class Screen:
    def __init__(self, device, width, height, park_label=""):
        self.device = device
        self.width = width
        self.height = height
        self.park_label = park_label
        self.scene = Scene(device)
        self._ghost = animations.GhostDrift(self.scene)

    def begin(self):
        """Paint the static scene once. Called from main.run() after construction."""
        self.device.clear()
        self.scene.draw_all()
        if self.park_label:
            self.scene.draw_park_label(self.park_label)

    def tick(self):
        """Cheap, non-blocking. Call every loop alongside candle.step()."""
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
        """Lightning strike. Replaces the old build's 3.2s bat-then-ghost
        sting -- the ghost now drifts on its own ~150-210s schedule via tick()."""
        animations.lightning(self.scene, self.park_label)


class ConsoleScreen:
    """Stands in for Screen when display_enabled is False -- prints what
    would have been shown instead, for bring-up testing on a breadboard
    before the TFT is wired up."""

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
