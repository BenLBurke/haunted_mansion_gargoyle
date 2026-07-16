# Chunky calculator-style digits so the wait-time number reads clearly on a
# tiny monochrome OLED without needing a bitmap font asset. The built-in
# framebuf 8x8 font is fine for labels but too small to be the star of the
# screen the way the number needs to be.
#
# Segment layout (standard 7-segment naming):
#   _a_
#  f   b
#   _g_
#  e   c
#   _d_

_SEGMENTS = {
    "0": "abcdef",
    "1": "bc",
    "2": "abged",
    "3": "abgcd",
    "4": "fgbc",
    "5": "afgcd",
    "6": "afgecd",
    "7": "abc",
    "8": "abcdefg",
    "9": "abcdfg",
}


def _digit(fb, x, y, w, h, digit, t, color):
    segs = _SEGMENTS[digit]
    half = h // 2
    if "a" in segs:
        fb.rect(x + t, y, w - 2 * t, t, color, True)
    if "d" in segs:
        fb.rect(x + t, y + h - t, w - 2 * t, t, color, True)
    if "g" in segs:
        fb.rect(x + t, y + half - t // 2, w - 2 * t, t, color, True)
    if "f" in segs:
        fb.rect(x, y + t, t, half - t, color, True)
    if "b" in segs:
        fb.rect(x + w - t, y + t, t, half - t, color, True)
    if "e" in segs:
        fb.rect(x, y + half, t, half - t, color, True)
    if "c" in segs:
        fb.rect(x + w - t, y + half, t, half - t, color, True)


def draw_number(fb, x, y, text, box_w=26, box_h=40, gap=6, thickness=4, color=1):
    """Draws `text` (digits only) left-to-right starting at (x, y)."""
    for ch in text:
        if ch in _SEGMENTS:
            _digit(fb, x, y, box_w, box_h, ch, thickness, color)
        x += box_w + gap


def measure(text, box_w=26, gap=6):
    if not text:
        return 0
    return len(text) * box_w + (len(text) - 1) * gap
