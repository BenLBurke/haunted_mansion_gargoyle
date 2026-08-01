"""High-level screen controller: wraps the device backend with rendering + animation playback."""

from __future__ import annotations

import time

from gargoyle.display import animations, renderer
from gargoyle.state import Snapshot


class Screen:
    def __init__(self, device, width: int, height: int):
        self.device = device
        self.width = width
        self.height = height

    def show_snapshot(self, snapshot: Snapshot, park_label: str, connected: bool) -> None:
        image = renderer.render_snapshot(self.width, self.height, snapshot, park_label, connected)
        self.device.display(image)

    def show_message(self, line1: str, line2: str = "") -> None:
        image = renderer.render_message(self.width, self.height, line1, line2)
        self.device.display(image)

    def play_wait_time_change_animation(self) -> None:
        for frame in animations.wait_time_change_frames(self.width, self.height):
            self.device.display(frame)
            time.sleep(animations.FRAME_DELAY_SECONDS)
