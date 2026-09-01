# Desktop stand-in for rdagger's ili9341.Display, so the TFT scene can be
# previewed as a PNG on a laptop instead of reflashing a Pico to see whether a
# spire is 4px off. Formalizes the PIL-stand-in approach animations.py already
# mentions.
#
# Runs under CPython with Pillow. Not shipped to the device.
#
#   cd pico-w
#   pip install pillow
#   python -m tools.preview            # writes preview.png
#   python -m tools.preview --wait 45  # with a specific wait time
#   python -m tools.preview --status DOWN
#   python -m tools.preview --frames   # numbered PNGs for a lightning sequence
#
# It implements only the driver surface scene.py / renderer_tft.py /
# animations_tft.py actually call. If you reach for another primitive, add it
# here and it stays previewable.

import argparse
import sys

from PIL import Image, ImageDraw

W, H = 320, 240


class FakeDisplay:
    """Quacks like ili9341.Display, draws into a Pillow image."""

    def __init__(self, width=W, height=H, scale=1):
        self.width = width
        self.height = height
        self.scale = scale
        self.img = Image.new("RGB", (width, height), (0, 0, 0))
        self.draw = ImageDraw.Draw(self.img)
        self.ops = 0          # primitive count -- a rough cost proxy
        self.pixels_touched = 0

    # --- color ---

    @staticmethod
    def color565(r, g, b):
        """Match the driver's packing, then unpack for preview, so the PNG
        shows the real 16-bit quantization (5-6-5) rather than full 24-bit.
        Banding you see here is banding you'll see on the panel."""
        return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

    @staticmethod
    def _unpack(c):
        r = (c >> 11) & 0x1F
        g = (c >> 5) & 0x3F
        b = c & 0x1F
        return (r << 3 | r >> 2, g << 2 | g >> 4, b << 3 | b >> 2)

    # --- primitives used by the reference modules ---

    def clear(self, color=0):
        self.draw.rectangle([0, 0, self.width, self.height], self._unpack(color))
        self.ops += 1

    def fill_rectangle(self, x, y, w, h, color):
        if w <= 0 or h <= 0:
            return
        self.draw.rectangle([x, y, x + w - 1, y + h - 1], self._unpack(color))
        self.ops += 1
        self.pixels_touched += w * h

    def fill_circle(self, x0, y0, r, color):
        self.draw.ellipse([x0 - r, y0 - r, x0 + r, y0 + r], self._unpack(color))
        self.ops += 1
        self.pixels_touched += int(3.14 * r * r)

    def draw_circle(self, x0, y0, r, color):
        self.draw.ellipse([x0 - r, y0 - r, x0 + r, y0 + r],
                          outline=self._unpack(color))
        self.ops += 1

    def fill_ellipse(self, x0, y0, a, b, color):
        self.draw.ellipse([x0 - a, y0 - b, x0 + a, y0 + b], self._unpack(color))
        self.ops += 1

    def draw_line(self, x0, y0, x1, y1, color):
        self.draw.line([x0, y0, x1, y1], self._unpack(color))
        self.ops += 1

    def draw_text8x8(self, x, y, text, color, background=0):
        """The real driver renders a fixed 8x8 bitmap font. Pillow's default
        font is close enough in metrics to judge layout and centering; do not
        trust it for exact glyph shapes."""
        self.draw.text((x, y), text, fill=self._unpack(color))
        self.ops += 1

    def block(self, x0, y0, x1, y1, data):
        """Raw RGB565 blit -- only used by the optional bg.raw fallback path."""
        w = x1 - x0 + 1
        for i in range(0, len(data), 2):
            c = (data[i] << 8) | data[i + 1]
            px = i // 2
            self.img.putpixel((x0 + px % w, y0 + px // w), self._unpack(c))
        self.ops += 1

    # --- output ---

    def save(self, path):
        img = self.img
        if self.scale != 1:
            img = img.resize((self.width * self.scale, self.height * self.scale),
                             Image.NEAREST)
        img.save(path)
        print("wrote {}  ({} primitives, ~{:,} px touched)".format(
            path, self.ops, self.pixels_touched))


# --- stand-ins for the device-only modules the reference code imports ---

class FakeAttraction:
    def __init__(self, status, wait_minutes):
        self.status = status
        self.wait_minutes = wait_minutes


class FakeSnapshot:
    def __init__(self, status="OPERATING", wait_minutes=45):
        self.attraction = FakeAttraction(status, wait_minutes)
        self.hours = None

    @property
    def phase(self):
        return "OPEN" if self.attraction.status != "CLOSED" else "CLOSED"


def _install_time_stub():
    """MicroPython's time has ticks_ms/ticks_diff/sleep_ms; CPython's doesn't.
    Patch them in so animations_tft imports cleanly off-device."""
    import time as _time
    if not hasattr(_time, "ticks_ms"):
        _time.ticks_ms = lambda: int(_time.monotonic() * 1000)
        _time.ticks_diff = lambda a, b: a - b
        _time.ticks_add = lambda a, b: a + b
        _time.sleep_ms = lambda ms: None      # no real waiting in preview
    return _time


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait", type=int, default=45)
    ap.add_argument("--status", default="OPERATING",
                    choices=["OPERATING", "CLOSED", "DOWN", "REFURBISHMENT", "UNKNOWN"])
    ap.add_argument("--park", default="Disneyland")
    ap.add_argument("--scale", type=int, default=2,
                    help="upscale the PNG for easier eyeballing")
    ap.add_argument("--stale", action="store_true", help="show the stale indicator")
    ap.add_argument("--ghost", type=int, default=None, metavar="X",
                    help="draw the ghost at this x, to check it over the facade")
    ap.add_argument("--flame", type=int, default=0, choices=[0, 1, 2, 3],
                    help="which of the 4 flame flicker steps to draw")
    ap.add_argument("--out", default="preview.png")
    args = ap.parse_args(argv)

    _install_time_stub()
    sys.path.insert(0, "src")

    from scene import Scene
    import renderer_tft as renderer
    import animations_tft as animations

    d = FakeDisplay(scale=args.scale)
    scene = Scene(d)

    scene.draw_all()
    scene.draw_park_label(args.park)

    renderer.render_snapshot(scene, FakeSnapshot(args.status, args.wait), True)

    if args.stale:
        renderer.render_stale_indicator(scene, True)

    animations.FlameFlicker(scene)._draw(args.flame)

    if args.ghost is not None:
        g = animations.GhostDrift(scene)
        g._x = args.ghost
        g._draw()

    d.save(args.out)


if __name__ == "__main__":
    main()
