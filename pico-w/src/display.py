# High-level screen controller: wraps the SSD1306 device with rendering + animation playback.

import animations
import renderer


def make_display(i2c_id, scl_pin, sda_pin, width, height, address):
    from machine import I2C, Pin
    from ssd1306 import SSD1306_I2C

    i2c = I2C(i2c_id, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=400_000)
    return SSD1306_I2C(width, height, i2c, addr=address)


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
