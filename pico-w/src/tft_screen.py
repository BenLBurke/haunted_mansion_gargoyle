# Adapter that lets the ILI9341 TFT stand in for the SSD1306 OLED. Screen
# (display.py) and everything it calls (renderer.py, animations.py,
# big_digits.py) only need fill/rect/ellipse/poly/line/text plus a .show()
# -- exactly what framebuf.FrameBuffer already provides -- so this just
# subclasses it the same way the vendored SSD1306_I2C does. None of that
# rendering code needed to change for a screen 18x the pixel count.
#
# The real constraint driving this design is RAM: 320x240 in full RGB565
# color would need a 150KB frame buffer -- more than half the Pico's total
# 264KB, and won't fit alongside WiFi/TLS. Instead this keeps rendering in
# 1-bit monochrome exactly like the OLED (320x240 at 1 bit/pixel is under
# 10KB) and only converts to color at the very last step -- see
# tft_render.py for the actual conversion/streaming logic, kept in its own
# module (no framebuf import) so it's testable under CPython the same way
# display.py's make_display() is lazy about importing machine/ssd1306.

import framebuf

from tft_render import build_lookup, stream_to_tft


class ILI9341Screen(framebuf.FrameBuffer):
    def __init__(self, width, height, spi, cs, dc, rst, rotation=90, fg_color=0xFD20, bg_color=0x0000):
        from ili9341 import Display

        self.width = width
        self.height = height

        # Row-major (MONO_HLSB, bit 7 = leftmost pixel) so the raw buffer
        # is already in the same left-to-right, top-to-bottom order the
        # panel's RAMWR window expects -- no transposing needed on the way out.
        self.buffer = bytearray((width * height) // 8)
        super().__init__(self.buffer, width, height, framebuf.MONO_HLSB)

        self.tft = Display(spi, cs, dc, rst, width=width, height=height, rotation=rotation)
        self._lut = build_lookup(fg_color, bg_color)

    def show(self):
        stream_to_tft(self.buffer, self.width, self.height, self._lut, self.tft.block)


def make_tft(
    spi_id,
    sck_pin,
    mosi_pin,
    miso_pin,
    cs_pin,
    dc_pin,
    rst_pin,
    width,
    height,
    rotation,
    fg_color,
    bg_color,
    baudrate=20_000_000,
):
    from machine import SPI, Pin

    spi = SPI(
        spi_id,
        baudrate=baudrate,
        polarity=0,
        phase=0,
        sck=Pin(sck_pin),
        mosi=Pin(mosi_pin),
        miso=Pin(miso_pin),
    )
    cs = Pin(cs_pin)
    dc = Pin(dc_pin)
    rst = Pin(rst_pin)
    return ILI9341Screen(width, height, spi, cs, dc, rst, rotation=rotation, fg_color=fg_color, bg_color=bg_color)
