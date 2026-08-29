# Draws the wait-time screen onto a framebuf-compatible object (an
# ssd1306.SSD1306_I2C instance satisfies this -- it subclasses
# framebuf.FrameBuffer directly).

import big_digits

STATUS_LABELS = {
    "DOWN": "TEMP DOWN",
    "REFURBISHMENT": "REFURB",
    "CLOSED": "CLOSED",
    "UNKNOWN": "NO DATA",
}


def _label_scale(width, height):
    """Bigger screens get bigger label text -- framebuf's built-in font has
    no native scale, so text_scale.py blits it pixel-doubled. Stays 1 (the
    plain fb.text() path, no framebuf needed) on the 128x64 OLED this was
    originally tuned for."""
    return max(1, min(width // 128, height // 64))


def _text_centered(fb, width, y, s, color=1, scale=1):
    char_w = 8 * scale
    x = max(0, (width - len(s) * char_w) // 2)
    if scale <= 1:
        fb.text(s, x, y, color)
    else:
        from text_scale import draw_scaled_text

        draw_scaled_text(fb, s, x, y, scale, color)


def render_snapshot(fb, width, height, snapshot, park_label, connected):
    fb.fill(0)
    scale = _label_scale(width, height)
    _text_centered(fb, width, 0, park_label.upper(), scale=scale)

    attraction = snapshot.attraction
    if attraction.status == "OPERATING" and attraction.wait_minutes is not None:
        text = str(attraction.wait_minutes)
        if len(text) <= 2:
            box_w, box_h, gap, thickness = 26, 36, 6, 4
        else:
            box_w, box_h, gap, thickness = 18, 36, 4, 3
        total_w = big_digits.measure(text, box_w, gap)
        x = max(0, (width - total_w) // 2)
        big_digits.draw_number(fb, x, 14, text, box_w, box_h, gap, thickness)
        _text_centered(fb, width, height - 8 * scale - 2, "MIN WAIT", scale=scale)
    else:
        label = STATUS_LABELS.get(attraction.status, attraction.status)
        _text_centered(fb, width, 26, label, scale=scale)
        hours_text = _hours_text(snapshot)
        if hours_text:
            _text_centered(fb, width, height - 8 * scale - 2, hours_text, scale=scale)

    if not connected:
        fb.text("!", width - 8, 0, 1)


def render_message(fb, width, height, line1, line2=""):
    fb.fill(0)
    scale = _label_scale(width, height)
    _text_centered(fb, width, height // 2 - 8 * scale, line1, scale=scale)
    if line2:
        _text_centered(fb, width, height // 2 + 2 * scale, line2, scale=scale)


def _hours_text(snapshot):
    hours = snapshot.hours
    if hours is None:
        return None
    if snapshot.phase == "CLOSED":
        return "Closed for the day"[:16]
    text = "{}-{}".format(hours.opening_text, hours.closing_text)
    return text[:16]
