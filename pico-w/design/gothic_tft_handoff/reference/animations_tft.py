# Motion for the 320x240 TFT build. Four effects, each scoped to a dirty rect
# except lightning, which is deliberately full-screen.
#
# Cadence is the whole point here: the user wants a near-still panel. Only the
# candle flame moves continuously (4 steps, 1.6s, ~448 bytes of SPI per frame).
# The ghost makes ONE pass every 150-210 seconds and is otherwise absent.
# Lightning fires only on an actual data change, never on a timer.
#
# This is a deliberate reversal of the OLED build's animations.py, where a
# 3.2-second bat-then-ghost sting fired on every wait change.

import random
import time

import scene as scene_mod

# ---- candle flame: 4 discrete steps, 1.6s loop ----
FLAME_PERIOD_MS = 400          # 4 steps x 400ms = 1.6s
FLAME_BODY = (255, 200, 113)   # #ffc871
FLAME_CORE = (255, 251, 238)   # #fffbee
FLAME_TIP  = (240, 116, 42)    # #f0742a

# (width, height, x_nudge) per step -- approximates the design's
# scale/rotate pairs: (1.00x1.00,-1.5), (0.86x1.22,+2), (1.12x0.88,-2.5), (0.94x1.14,+1)
FLAME_STEPS = ((3, 7, 0), (3, 9, 1), (4, 6, -1), (3, 8, 0))


class FlameFlicker:
    def __init__(self, scene):
        self.s = scene
        self._i = 0
        self._last = time.ticks_ms()

    def tick(self):
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last) < FLAME_PERIOD_MS:
            return
        self._last = now
        self._i = (self._i + 1) % len(FLAME_STEPS)
        self._draw(self._i)

    def _draw(self, i):
        w, h, nudge = FLAME_STEPS[i]
        rx, ry, rw, rh = scene_mod.R_FLAME
        self.s.restore(scene_mod.R_FLAME)
        cx = rx + rw // 2 + nudge
        base = ry + rh - 1
        d = self.s.d
        for row in range(h):
            t = row / max(1, h - 1)
            span = max(1, int(w * (1.0 - t * 0.75)))
            color = self.s.rgb(scene_mod._lerp(FLAME_BODY, FLAME_TIP, t)) if t > 0.5 \
                else self.s.rgb(scene_mod._lerp(FLAME_CORE, FLAME_BODY, t * 2))
            d.fill_rectangle(cx - span // 2, base - row, span, 1, color)


# ---- ghost: one drift pass every 150-210s ----
GHOST_BODY = (141, 134, 163)   # #8d86a3
GHOST_EDGE = (74, 68, 89)      # #4a4459
GHOST_EYE  = (36, 26, 51)      # #241a33
GHOST_STEP_PX = 6
GHOST_STEP_MS = 60


class GhostDrift:
    def __init__(self, scene):
        self.s = scene
        self._next = time.time() + random.randint(30, 90)   # first pass sooner
        self._x = None
        self._last = 0

    def tick(self):
        if self._x is None:
            if time.time() < self._next:
                return
            self._x = -scene_mod.GHOST_W
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last) < GHOST_STEP_MS:
            return
        self._last = now
        self._erase()
        self._x += GHOST_STEP_PX
        if self._x > scene_mod.W:
            self._x = None
            self._next = time.time() + random.randint(150, 210)
            return
        self._draw()

    def _rect(self, x):
        return (max(0, x), scene_mod.GHOST_Y, scene_mod.GHOST_W, scene_mod.GHOST_H)

    def _erase(self):
        self.s.restore(self._rect(self._x))

    def _draw(self):
        """Dome + torso + scalloped hem -- the same silhouette instinct as the
        OLED build's _ghost_frame(), in color, with no alpha available."""
        d = self.s.d
        x, y, w, h = self._rect(self._x)
        if x + w > scene_mod.W:
            w = scene_mod.W - x
        if w <= 2:
            return
        cx = x + w // 2
        r = scene_mod.GHOST_W // 2
        body = self.s.rgb(GHOST_BODY)
        edge = self.s.rgb(GHOST_EDGE)
        d.fill_circle(cx, y + r, r, edge)
        d.fill_circle(cx, y + r, r - 2, body)
        d.fill_rectangle(x + 1, y + r, w - 2, h - r - 4, body)
        # scalloped hem: three notches punched back to background
        notch = max(2, w // 3)
        for i in range(3):
            nx = x + i * notch + notch // 2
            self.s.restore((max(0, nx - notch // 2), y + h - 5, notch, 5))
        # eyes
        d.fill_rectangle(cx - 6, y + r - 2, 3, 4, self.s.rgb(GHOST_EYE))
        d.fill_rectangle(cx + 3, y + r - 2, 3, 4, self.s.rgb(GHOST_EYE))


# ---- lightning: only on a real data change ----
# Design keyframes over 900ms: 0 -> .92 @4% -> .05 @10% -> .75 @16% -> .02 @24%
# -> .45 @34% -> 0. Two bright strikes plus a dim afterglow. On device this
# becomes flat fills with holds; ~150ms per full-screen push at 40MHz.
STRIKES = ((255, 252, 240, 60),   # r, g, b, hold_ms
           (214, 206, 255, 40),
           (180, 170, 230, 30))


def lightning(scene, park_label=""):
    d = scene.d
    for (r, g, b, hold) in STRIKES:
        d.fill_rectangle(0, 0, scene_mod.W, scene_mod.H, scene.rgb((r, g, b)))
        time.sleep_ms(hold)
        scene.draw_all()
        if park_label:
            scene.draw_park_label(park_label)
        time.sleep_ms(70)


# ---- numeral roll-in ----
# Design: 480ms, cubic-bezier(.2,.8,.2,1), translateY +26 -> 0, scale .94 -> 1.
# On device: drop the scale, step translateY over ~8 frames inside R_NUMERAL,
# restoring the tombstone patch each frame.
ROLL_FRAMES = 8
ROLL_OFFSET_PX = 26


def _ease_out(t):
    return 1 - (1 - t) ** 3


def roll_in(scene, draw_digits):
    """draw_digits(y_offset) must render the numeral shifted down by y_offset,
    clipped to scene.R_NUMERAL."""
    for i in range(ROLL_FRAMES):
        t = _ease_out((i + 1) / ROLL_FRAMES)
        scene.restore(scene_mod.R_NUMERAL)
        draw_digits(int(ROLL_OFFSET_PX * (1 - t)))
        time.sleep_ms(40)
