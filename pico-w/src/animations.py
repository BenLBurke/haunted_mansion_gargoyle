# Procedurally drawn ghost/bat animation played briefly whenever the wait
# time changes. Drawn with plain framebuf primitives -- no sprite assets --
# geometry was prototyped and eyeballed with a PIL stand-in before porting
# here, since there's no way to preview framebuf output off-device.

from array import array

FRAME_DELAY_MS = 80


def _bat_frame(fb, width, height, x, y, wing_lift, color=1):
    fb.ellipse(x, y, 3, 3, color, True)
    left_wing = array("h", [0, 0, -12, -wing_lift, -6, 2])
    right_wing = array("h", [0, 0, 12, -wing_lift, 6, 2])
    fb.poly(x, y, left_wing, color, True)
    fb.poly(x, y, right_wing, color, True)
    fb.line(x - 2, y - 3, x - 3, y - 7, color)
    fb.line(x + 2, y - 3, x + 3, y - 7, color)


def _ghost_frame(fb, cx, cy, scale, color=1, bg=0):
    body_w = int(22 * scale)
    body_h = int(26 * scale)
    if body_w < 6 or body_h < 10:
        return
    left = cx - body_w // 2
    top = cy - body_h // 2
    bottom = top + body_h
    head_r = body_w // 2

    fb.ellipse(cx, top + head_r, head_r, head_r, color, True, 0b0011)  # rounded dome
    torso_top = top + head_r
    fb.rect(left, torso_top, body_w, bottom - torso_top, color, True)

    scallop_w = max(2, body_w // 3)
    notch_r = scallop_w // 2 + 1
    for i in range(3):
        sx = left + i * scallop_w + scallop_w // 2
        fb.ellipse(sx, bottom, notch_r, notch_r, bg, True, 0b0011)  # scalloped hem

    if scale > 0.4:
        eye_y = top + head_r
        fb.rect(cx - 6, eye_y, 3, 4, bg, True)
        fb.rect(cx + 3, eye_y, 3, 4, bg, True)


def play(fb, width, height, show, sleep_ms, frame_count=20):
    """Runs the full bat-then-ghost sting on the given framebuf, calling
    `show()` and `sleep_ms(FRAME_DELAY_MS)` after each frame. `fb` needs
    fill/ellipse/rect/poly/line (framebuf.FrameBuffer satisfies this)."""
    y_center = height // 2

    for i in range(frame_count):
        t = i / (frame_count - 1)
        x = int(-16 + t * (width + 32))
        wing_lift = int(8 * _sin(t * 6))
        y = y_center + int(6 * _sin(t * 3))
        fb.fill(0)
        _bat_frame(fb, width, height, x, y, wing_lift)
        show()
        sleep_ms(FRAME_DELAY_MS)

    x_center = width // 2
    for i in range(frame_count):
        t = i / (frame_count - 1)
        bob = int(4 * _sin(t * 2))
        if t < 0.2:
            scale = t / 0.2
        elif t > 0.8:
            scale = (1.0 - t) / 0.2
        else:
            scale = 1.0
        fb.fill(0)
        _ghost_frame(fb, x_center, y_center + bob, scale)
        show()
        sleep_ms(FRAME_DELAY_MS)


def _sin(x):
    # MicroPython's math.sin takes radians same as CPython; x here is already
    # in "half turns" (matches the Pi version's math.pi * n phase multiplier).
    import math

    return math.sin(x * math.pi)
