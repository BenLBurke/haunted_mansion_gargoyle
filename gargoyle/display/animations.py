"""Procedurally drawn ghost/bat animation shown briefly whenever the wait time changes.

Frames are drawn with plain PIL primitives rather than sprite assets, so the
whole thing stays text-only and needs no binary files in the repo.
"""

from __future__ import annotations

import math

from PIL import Image, ImageDraw

FRAME_DELAY_SECONDS = 0.08


def bat_flight_frames(width: int, height: int, frame_count: int = 20) -> list[Image.Image]:
    frames = []
    y_center = height // 2
    for i in range(frame_count):
        t = i / (frame_count - 1)
        x = int(-16 + t * (width + 32))
        wing_phase = math.sin(t * math.pi * 6)
        y = y_center + int(6 * math.sin(t * math.pi * 3))
        frames.append(_bat_frame(width, height, x, y, wing_phase))
    return frames


def ghost_float_frames(width: int, height: int, frame_count: int = 20) -> list[Image.Image]:
    frames = []
    x_center = width // 2
    y_center = height // 2
    for i in range(frame_count):
        t = i / (frame_count - 1)
        bob = int(4 * math.sin(t * math.pi * 2))
        # Fade in for the first quarter, hold, fade out for the last quarter.
        if t < 0.2:
            scale = t / 0.2
        elif t > 0.8:
            scale = (1.0 - t) / 0.2
        else:
            scale = 1.0
        frames.append(_ghost_frame(width, height, x_center, y_center + bob, scale))
    return frames


def wait_time_change_frames(width: int, height: int) -> list[Image.Image]:
    """The full haunted sting shown on a wait-time change: bat flies through, ghost lingers."""
    return bat_flight_frames(width, height) + ghost_float_frames(width, height)


def _bat_frame(width: int, height: int, x: int, y: int, wing_phase: float) -> Image.Image:
    image = Image.new("1", (width, height), 0)
    draw = ImageDraw.Draw(image)

    wing_lift = int(8 * wing_phase)
    # Body.
    draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=1)
    # Wings as triangles that flap up and down with wing_phase.
    draw.polygon([(x, y), (x - 12, y - wing_lift), (x - 6, y + 2)], fill=1)
    draw.polygon([(x, y), (x + 12, y - wing_lift), (x + 6, y + 2)], fill=1)
    # Ears.
    draw.line((x - 2, y - 3, x - 3, y - 7), fill=1)
    draw.line((x + 2, y - 3, x + 3, y - 7), fill=1)
    return image


def _ghost_frame(width: int, height: int, cx: int, cy: int, scale: float) -> Image.Image:
    image = Image.new("1", (width, height), 0)
    body_w = int(22 * scale)
    body_h = int(26 * scale)
    if body_w < 6 or body_h < 10:
        return image
    draw = ImageDraw.Draw(image)

    left = cx - body_w // 2
    right = cx + body_w // 2
    top = cy - body_h // 2
    bottom = cy + body_h // 2

    # Rounded head/torso.
    draw.pieslice((left, top, right, top + body_h), start=180, end=360, fill=1)
    rect_top = top + body_h // 2
    rect_bottom = max(rect_top, bottom - 6)
    draw.rectangle((left, rect_top, right, rect_bottom), fill=1)

    # Wavy bottom hem, three scallops.
    scallop_w = body_w / 3
    hem_top = max(top, bottom - 12)
    for i in range(3):
        sx = left + i * scallop_w
        draw.pieslice((sx, hem_top, sx + scallop_w, bottom), start=0, end=180, fill=0)

    # Eyes.
    if scale > 0.4:
        eye_y = top + body_h // 3
        draw.ellipse((cx - 6, eye_y, cx - 3, eye_y + 4), fill=0)
        draw.ellipse((cx + 3, eye_y, cx + 6, eye_y + 4), fill=0)

    return image
