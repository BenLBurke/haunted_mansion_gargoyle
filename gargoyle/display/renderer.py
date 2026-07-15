"""Draws the wait-time screen for the OLED."""

from __future__ import annotations

import datetime as dt

from PIL import Image, ImageDraw, ImageFont

from gargoyle.state import ParkPhase, Snapshot

STATUS_LABELS = {
    "OPERATING": None,  # normal case, wait time shown instead
    "DOWN": "TEMP. DOWN",
    "REFURBISHMENT": "REFURBISHMENT",
    "CLOSED": "CLOSED",
    "UNKNOWN": "NO DATA",
}


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        # Older Pillow: load_default() takes no size argument.
        return ImageFont.load_default()


FONT_SMALL = _font(11)
FONT_MEDIUM = _font(16)
FONT_LARGE = _font(28)


def render_snapshot(width: int, height: int, snapshot: Snapshot, park_label: str, connected: bool) -> Image.Image:
    image = Image.new("1", (width, height), 0)
    draw = ImageDraw.Draw(image)

    _draw_centered(draw, width, 0, park_label.upper(), FONT_SMALL)

    attraction = snapshot.attraction
    label = STATUS_LABELS.get(attraction.status, attraction.status)
    if attraction.status == "OPERATING" and attraction.wait_minutes is not None:
        _draw_centered(draw, width, 14, f"{attraction.wait_minutes}", FONT_LARGE)
        _draw_centered(draw, width, height - 16, "MINUTES WAIT", FONT_SMALL)
    else:
        if label:
            _draw_centered(draw, width, 22, label, FONT_MEDIUM)
        hours_text = _hours_text(snapshot)
        if hours_text:
            _draw_centered(draw, width, height - 16, hours_text, FONT_SMALL)

    if not connected:
        draw.text((width - 10, 0), "!", font=FONT_SMALL, fill=1)

    return image


def render_message(width: int, height: int, line1: str, line2: str = "") -> Image.Image:
    image = Image.new("1", (width, height), 0)
    draw = ImageDraw.Draw(image)
    _draw_centered(draw, width, height // 2 - 14, line1, FONT_SMALL)
    if line2:
        _draw_centered(draw, width, height // 2 + 2, line2, FONT_SMALL)
    return image


def _hours_text(snapshot: Snapshot) -> str | None:
    hours = snapshot.hours
    if hours is None or hours.opening_time is None or hours.closing_time is None:
        return None
    if snapshot.phase == ParkPhase.CLOSED:
        return "Closed for the day"
    return f"{_fmt(hours.opening_time)} - {_fmt(hours.closing_time)}"


def _fmt(t: dt.datetime) -> str:
    local = t.astimezone()
    return local.strftime("%-I:%M%p").lower()


def _draw_centered(draw: ImageDraw.ImageDraw, width: int, y: int, text: str, font: ImageFont.ImageFont) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = max(0, (width - text_width) // 2)
    draw.text((x, y), text, font=font, fill=1)
