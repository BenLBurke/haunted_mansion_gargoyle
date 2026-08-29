# framebuf.text() draws a fixed 8x8-pixel font with no scale parameter --
# fine on the 128x64 OLED, but tiny on a 320x240 TFT. This blits it bigger
# by rendering at 1x into a small scratch FrameBuffer (still using the
# built-in font, so no custom glyphs to author/maintain) and re-drawing each
# set pixel as an NxN block on the real destination.
#
# Needs a real framebuf.FrameBuffer for that scratch buffer, so -- like
# display.py/tft_screen.py -- this can't run under CPython. renderer.py only
# imports it lazily, when an actual scale-up is needed, so the rest of
# renderer.py (and the scale=1 path here) stay usable off-device.

import framebuf


def draw_scaled_text(fb, s, x, y, scale, color=1):
    if scale <= 1:
        fb.text(s, x, y, color)
        return

    width, height = len(s) * 8, 8
    stride = (width + 7) // 8
    scratch = framebuf.FrameBuffer(bytearray(stride * height), width, height, framebuf.MONO_HLSB)
    scratch.text(s, 0, 0, 1)

    for row in range(height):
        for col in range(width):
            if scratch.pixel(col, row):
                fb.rect(x + col * scale, y + row * scale, scale, scale, color, True)
