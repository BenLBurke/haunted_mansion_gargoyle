# Procedurally drawn ghost/bat animation played briefly whenever the wait
# time changes. Drawn with plain framebuf primitives -- no sprite assets --
# geometry was prototyped and eyeballed with a PIL stand-in before porting
# here, since there's no way to preview framebuf output off-device.
#
# All the pixel constants below were tuned by eye against the 128x64 OLED;
# `play()` derives a size scale from the actual screen dimensions (1.0 on
# that same 128x64 OLED, so this is unchanged there) so the same shapes read
# proportionally on a much bigger canvas -- e.g. the 320x240 TFT -- instead
# of looking tiny in the corner.

from array import array

FRAME_DELAY_MS = 80


def _bat_frame(fb, x, y, wing_lift, scale, color=1):
    r = max(1, int(3 * scale))
    fb.ellipse(x, y, r, r, color, True)
    lift = int(wing_lift)
    left_wing = array("h", [0, 0, int(-12 * scale), -lift, int(-6 * scale), int(2 * scale)])
    right_wing = array("h", [0, 0, int(12 * scale), -lift, int(6 * scale), int(2 * scale)])
    fb.poly(x, y, left_wing, color, True)
    fb.poly(x, y, right_wing, color, True)
    dx, dy1, dy2 = int(2 * scale), int(3 * scale), int(7 * scale)
    fb.line(x - dx, y - dy1, x - dx - 1, y - dy2, color)
    fb.line(x + dx, y - dy1, x + dx + 1, y - dy2, color)


def _ghost_frame(fb, cx, cy, pulse, scale, color=1, bg=0):
    body_w = int(22 * scale * pulse)
    body_h = int(26 * scale * pulse)
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

    if pulse > 0.4:
        eye_w, eye_h = max(2, int(3 * scale)), max(2, int(4 * scale))
        eye_dx = max(4, int(6 * scale))
        eye_y = top + head_r
        fb.rect(cx - eye_dx, eye_y, eye_w, eye_h, bg, True)
        fb.rect(cx + eye_dx - eye_w, eye_y, eye_w, eye_h, bg, True)


def play(fb, width, height, show, sleep_ms, frame_count=20):
    """Runs the full bat-then-ghost sting on the given framebuf, calling
    `show()` and `sleep_ms(FRAME_DELAY_MS)` after each frame. `fb` needs
    fill/ellipse/rect/poly/line (framebuf.FrameBuffer satisfies this)."""
    y_center = height // 2
    scale = min(width / 128.0, height / 64.0)
    margin = int(16 * scale)

    for i in range(frame_count):
        t = i / (frame_count - 1)
        x = int(-margin + t * (width + 2 * margin))
        wing_lift = 8 * scale * _sin(t * 6)
        y = y_center + int(6 * scale * _sin(t * 3))
        fb.fill(0)
        _bat_frame(fb, x, y, wing_lift, scale)
        show()
        sleep_ms(FRAME_DELAY_MS)

    x_center = width // 2
    for i in range(frame_count):
        t = i / (frame_count - 1)
        bob = int(4 * scale * _sin(t * 2))
        if t < 0.2:
            pulse = t / 0.2
        elif t > 0.8:
            pulse = (1.0 - t) / 0.2
        else:
            pulse = 1.0
        fb.fill(0)
        _ghost_frame(fb, x_center, y_center + bob, pulse, scale)
        show()
        sleep_ms(FRAME_DELAY_MS)


def _sin(x):
    # MicroPython's math.sin takes radians same as CPython; x here is already
    # in "half turns" (matches the Pi version's math.pi * n phase multiplier).
    import math

    return math.sin(x * math.pi)
