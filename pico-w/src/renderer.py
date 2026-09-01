# Draws the wait-time content onto the 320x240 TFT.
#
# Two departures from the SSD1306 renderer.py this replaces:
#
#   1. NOTHING is cleared. The static gothic scene (scene.py) is painted once
#      at boot and must survive; only the numeral or message rect is repainted.
#      There is no framebuf and no .show().
#   2. On a fetch failure the numeral is LEFT ALONE. An always-on ambient
#      display is more useful showing a stale wait time than an error, so
#      failures draw a small quiet indicator and nothing else.

import big_digits
import scene as scene_mod

NUMERAL   = (255, 215, 154)   # #ffd79a
UNIT      = (216, 206, 184)   # #d8ceb8
MESSAGE   = (226, 214, 189)   # #e2d6bd
STALE     = (169, 156, 184)   # #a99cb8

MSG_CLOSED = "Closed"
MSG_DOWN = ("Playful spooks have interrupted the tour",
            "Unavoidably detained by pranky spirits")

# Per the handoff: REFURBISHMENT reads better in-fiction than "REFURB".
STATUS_MESSAGES = {
    "CLOSED": MSG_CLOSED,
    "REFURBISHMENT": MSG_DOWN[1],
    "UNKNOWN": "Lost the signal...",
}

_STALE_RECT = (8, 9, 8, 8)


def unit_label(wait):
    if wait >= 999:
        return "AN ETERNITY"
    return "MINUTE" if wait == 1 else "MINUTES"


def render_snapshot(scene, snapshot, connected):
    attraction = snapshot.attraction
    if attraction.status == "OPERATING" and attraction.wait_minutes is not None:
        render_number(scene, attraction.wait_minutes)
        render_stale_indicator(scene, False)
    elif attraction.status == "DOWN":
        render_message_block(scene, MSG_DOWN[0])
    else:
        render_message_block(scene, STATUS_MESSAGES.get(attraction.status, attraction.status))


def render_number(scene, wait, y_offset=0):
    """Repaints only R_NUMERAL. y_offset supports the roll-in animation."""
    x, y, w, h = scene_mod.R_NUMERAL
    scene.restore(scene_mod.R_NUMERAL)

    text = str(wait)
    box_w, box_h, gap, thickness = (44, 66, 8, 8) if len(text) <= 2 else (26, 66, 5, 6)
    total = big_digits.measure(text, box_w, gap)
    dx = x + max(0, (w - total) // 2)
    dy = y + max(0, (h - box_h) // 2) + y_offset
    big_digits.draw_number(scene.d, dx, dy, text, box_w, box_h, gap,
                           thickness, scene.rgb(NUMERAL))

    label = unit_label(wait)
    lx = max(0, (scene_mod.W - len(label) * 8) // 2)
    ly = scene_mod.TS_Y + scene_mod.TS_H - 24
    scene.restore((0, ly, scene_mod.W, 10))
    scene.d.draw_text8x8(lx, ly, label, scene.rgb(UNIT))


def render_message_block(scene, text):
    """Replaces the numeral with a centered wrapped message inside the stone."""
    x, y, w, h = scene_mod.R_MESSAGE
    scene.restore(scene_mod.R_MESSAGE)
    scene.restore((0, scene_mod.TS_Y + scene_mod.TS_H - 24, scene_mod.W, 10))

    lines = _wrap(text, w // 8)
    ly = y + max(0, (h - len(lines) * 12) // 2)
    for i, line in enumerate(lines):
        lx = x + max(0, (w - len(line) * 8) // 2)
        scene.d.draw_text8x8(lx, ly + i * 12, line, scene.rgb(MESSAGE))


def render_message(scene, line1, line2=""):
    """Boot / provisioning messages, before there is any number to preserve."""
    render_message_block(scene, (line1 + " " + line2).strip())


def render_stale_indicator(scene, on):
    """Quiet corner mark meaning 'this number is older than it should be'.
    Never touches the numeral. Mirrors where the OLED build drew its '!'."""
    x, y, w, h = _STALE_RECT
    scene.restore(_STALE_RECT)
    if on:
        # A small dim crescent reads better than a warning glyph.
        scene.d.fill_circle(x + 4, y + 4, 4, scene.rgb(STALE))
        scene.d.fill_circle(x + 6, y + 3, 3, scene.rgb(scene_mod.SKY_TOP))


def _wrap(text, cols):
    words = text.split(" ")
    lines, cur = [], ""
    for word in words:
        candidate = word if not cur else cur + " " + word
        if len(candidate) <= cols:
            cur = candidate
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines
