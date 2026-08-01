"""Picks a real SSD1306 OLED device on a Pi, or a file-dumping mock everywhere else."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

log = logging.getLogger(__name__)


class MockScreen:
    """Stands in for the luma.oled device when not running on real hardware.

    Writes each frame to a PNG so you can eyeball the UI while developing off-Pi.
    """

    def __init__(self, width: int, height: int, out_path: str = "/tmp/gargoyle_screen.png"):
        self.width = width
        self.height = height
        self.out_path = Path(out_path)
        self.last_image: Image.Image | None = None

    def display(self, image: Image.Image) -> None:
        self.last_image = image
        try:
            image.save(self.out_path)
        except OSError:
            log.debug("could not write mock screen frame to %s", self.out_path, exc_info=True)


def make_screen(width: int, height: int, i2c_port: int, i2c_address: int, simulate: bool):
    if simulate:
        return MockScreen(width, height)
    try:
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306

        serial = i2c(port=i2c_port, address=i2c_address)
        return ssd1306(serial, width=width, height=height)
    except Exception:
        log.warning("luma.oled unavailable, falling back to mock screen", exc_info=True)
        return MockScreen(width, height)
