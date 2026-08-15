# High-level screen controller: wraps the SSD1306 device with rendering + animation playback.

import animations
import renderer


def make_display(config):
    """Builds whichever display device config["display_driver"] selects.
    Both devices are framebuf.FrameBuffer subclasses with the same
    fill/rect/ellipse/poly/line/text + show() surface, so Screen below
    doesn't need to know or care which one it got."""
    driver = config.get("display_driver", "ssd1306")

    if driver == "ili9341":
        from tft_screen import make_tft

        return make_tft(
            config["tft_spi_id"],
            config["tft_sck_pin"],
            config["tft_mosi_pin"],
            config["tft_miso_pin"],
            config["tft_cs_pin"],
            config["tft_dc_pin"],
            config["tft_rst_pin"],
            config["display_width"],
            config["display_height"],
            config["tft_rotation"],
            config["tft_fg_color"],
            config["tft_bg_color"],
        )

    if driver != "ssd1306":
        raise ValueError("unknown display_driver: {}".format(driver))

    from machine import I2C, Pin
    from ssd1306 import SSD1306_I2C

    i2c = I2C(config["i2c_id"], scl=Pin(config["i2c_scl_pin"]), sda=Pin(config["i2c_sda_pin"]), freq=400_000)
    return SSD1306_I2C(config["display_width"], config["display_height"], i2c, addr=config["display_i2c_address"])


class Screen:
    def __init__(self, device, width, height):
        self.device = device
        self.width = width
        self.height = height

    def show_snapshot(self, snapshot, park_label, connected):
        renderer.render_snapshot(self.device, self.width, self.height, snapshot, park_label, connected)
        self.device.show()

    def show_message(self, line1, line2=""):
        renderer.render_message(self.device, self.width, self.height, line1, line2)
        self.device.show()

    def play_wait_time_change_animation(self):
        import utime

        animations.play(self.device, self.width, self.height, self.device.show, utime.sleep_ms)


class ConsoleScreen:
    """Stands in for Screen when display_enabled is False -- prints what
    would have been shown to the serial console instead, for bring-up
    testing on a breadboard before the OLED is wired up."""

    def show_snapshot(self, snapshot, park_label, connected):
        attraction = snapshot.attraction
        if attraction.status == "OPERATING" and attraction.wait_minutes is not None:
            status = "{} min wait".format(attraction.wait_minutes)
        else:
            status = attraction.status

        hours = ""
        if snapshot.hours is not None:
            hours = " ({}-{})".format(snapshot.hours.opening_text, snapshot.hours.closing_text)

        print("[screen] {}: {}{} (connected={})".format(park_label, status, hours, connected))

    def show_message(self, line1, line2=""):
        print("[screen] {} {}".format(line1, line2).rstrip())

    def play_wait_time_change_animation(self):
        print("[screen] (ghost/bat animation would play here)")
