# Slab-serif 7-segment digits for the tombstone numeral -- procedural, no
# font asset, keeping the "no font asset" convention of the original OLED
# build's calculator-style digits. Restyled per the gothic-mansion design
# brief to read as engraved stone rather than a calculator display:
# heavier vertical stems than horizontals, a serif cap block at each loose
# stroke terminal, and rounded corners (via fill_circle) on the curved
# digits (0/6/8/9) instead of sharp right angles.
#
# `fb` here is the raw ILI9341 driver (or its Pillow preview stand-in), not
# a framebuf.FrameBuffer -- draws go through fill_rectangle()/fill_circle(),
# matching the rest of the TFT build (see scene.py).
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

# Digits with a curved bowl get rounded corners instead of serif caps.
_ROUNDED = set("03689")


def _h_seg(fb, x, cy, w, thick, color, serif):
    """Horizontal segment centered on row `cy`, spanning [x, x+w)."""
    fb.fill_rectangle(x, cy - thick // 2, w, thick, color)
    if serif:
        cap = thick + 2
        fb.fill_rectangle(x, cy - cap // 2, 2, cap, color)
        fb.fill_rectangle(x + w - 2, cy - cap // 2, 2, cap, color)


def _v_seg(fb, cx, y, h, thick, color, serif):
    """Vertical segment centered on column `cx`, spanning [y, y+h)."""
    fb.fill_rectangle(cx - thick // 2, y, thick, h, color)
    if serif:
        cap = thick + 2
        fb.fill_rectangle(cx - cap // 2, y, cap, 2, color)
        fb.fill_rectangle(cx - cap // 2, y + h - 2, cap, 2, color)


def _digit(fb, x, y, w, h, digit, thickness, color):
    segs = _SEGMENTS[digit]
    half = h // 2
    v_thick = thickness
    h_thick = max(2, int(thickness * 0.75))  # horizontals read lighter than stems
    rounded = digit in _ROUNDED
    serif = not rounded

    cx_l, cx_r = x, x + w
    cy_t, cy_m, cy_b = y, y + half, y + h

    if "a" in segs:
        _h_seg(fb, x, cy_t, w, h_thick, color, serif)
    if "g" in segs:
        _h_seg(fb, x, cy_m, w, h_thick, color, serif)
    if "d" in segs:
        _h_seg(fb, x, cy_b, w, h_thick, color, serif)
    if "f" in segs:
        _v_seg(fb, cx_l, cy_t, half, v_thick, color, serif)
    if "b" in segs:
        _v_seg(fb, cx_r, cy_t, half, v_thick, color, serif)
    if "e" in segs:
        _v_seg(fb, cx_l, cy_m, half, v_thick, color, serif)
    if "c" in segs:
        _v_seg(fb, cx_r, cy_m, half, v_thick, color, serif)

    if rounded:
        r = max(1, h_thick // 2)
        for (cx, cy, present) in (
            (cx_l, cy_t, "a" in segs and "f" in segs),
            (cx_r, cy_t, "a" in segs and "b" in segs),
            (cx_l, cy_b, "d" in segs and "e" in segs),
            (cx_r, cy_b, "d" in segs and "c" in segs),
        ):
            if present:
                fb.fill_circle(cx, cy, r, color)


def draw_number(fb, x, y, text, box_w=44, box_h=66, gap=8, thickness=8, color=1):
    """Draws `text` (digits only) left-to-right starting at (x, y)."""
    for ch in text:
        if ch in _SEGMENTS:
            _digit(fb, x, y, box_w, box_h, ch, thickness, color)
        x += box_w + gap


def measure(text, box_w=44, gap=8):
    if not text:
        return 0
    return len(text) * box_w + (len(text) - 1) * gap
