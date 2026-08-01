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
