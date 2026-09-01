# Static gothic mansion scene for the 320x240 SPI TFT.
#
# Drawn ONCE at boot (see display.Screen.begin), then small patches are
# redrawn on demand under moving elements. There is deliberately no full
# framebuffer: 320*240*2 = 153,600 bytes against 264KB of SRAM, and WiFi/TLS
# wants 40-50KB during a request.
#
# Written against rdagger's ili9341.py. Note that driver's fill_polygon()
# draws REGULAR polygons (sides + radius) only, so the triangles and pointed
# arches this scene needs get scanline helpers below.
#
# Geometry comes from panel 1B of "Haunted Mansion Wait Display.dc.html".
# Y coordinates in the facade section are measured from the BOTTOM of the
# panel, matching the design doc; _fb() converts to top-origin.

W, H = 320, 240

# ---- palette (RGB triples; convert with display.color565) ----
SKY_TOP      = (12, 8, 19)      # #0c0813
SKY_MID      = (27, 18, 38)     # #1b1226
SKY_BOTTOM   = (51, 32, 69)     # #332045
SILHOUETTE   = (10, 6, 16)      # #0a0610
BODY         = (11, 7, 17)      # #0b0711
WINDOW_DARK  = (5, 3, 9)        # #050309
MOON_CORE    = (246, 230, 196)  # #f6e6c4
MOON_MID     = (216, 191, 148)  # #d8bf94
MOON_EDGE    = (166, 139, 98)   # #a68b62
STAR_A       = (103, 99, 90)    # #cfc6b4 at ~50% over sky
STAR_B       = (92, 87, 100)    # #b8afc9 at ~50% over sky
STONE_TOP    = (100, 92, 108)   # #645c6c
STONE_MID    = (68, 62, 77)     # #443e4d
STONE_BOT    = (48, 43, 57)     # #302b39
STONE_EDGE   = (90, 86, 100)
LABEL_DIM    = (184, 175, 192)  # #b8afc0
PARK_LABEL   = (169, 156, 184)  # #a99cb8
TITLE        = (231, 220, 198)  # #e7dcc6
ROSE_CORE    = (224, 155, 65)   # #e09b41
ROSE_EDGE    = (109, 65, 22)    # #6d4116
GLOW_RING_1  = (58, 42, 46)
GLOW_RING_2  = (34, 26, 36)

# Lancet window gradients, top -> 60% -> bottom
WIN_LIT  = ((255, 208, 143), (224, 144, 47), (148, 87, 28))
WIN_DIM1 = ((160, 108, 46), (91, 53, 20), (56, 32, 12))
WIN_DIM2 = ((201, 135, 58), (126, 77, 28), (74, 44, 16))

# The sky gradient's 3 stops, as (t, rgb) over the full panel height -- used
# both by draw_sky() and by restore() so an erased patch samples the SAME
# curve the background was actually painted with, rather than treating
# itself as its own independent 0..1 gradient (that mismatch was the ghost's
# visible trailing line/flicker: every erase painted the wrong color, then
# the ghost got redrawn on top of it).
SKY_STOPS = ((0.0, SKY_TOP), (0.56, SKY_MID), (1.0, SKY_BOTTOM))

# ---- dirty rects (x, y, w, h), top-origin ----
# Full tombstone width (matches the numeral div's real CSS: width:100% of
# the 150px stone) -- it was previously only 84px, narrower than a 2-digit
# number actually renders at (96px), which silently broke centering.
R_NUMERAL = (85, 66, 150, 88)
# Message div is CSS left:12,top:44,right:12,bottom:20 within the 150x158
# tombstone: h = 158-44-20 = 94, not the shorter 62 this was originally
# transcribed as -- that left an unrestored 28px gap between this rect and
# the separately-cleared unit-label strip, which could show stale pixels.
R_MESSAGE = (97, 76, 126, 94)
GHOST_W, GHOST_H, GHOST_Y = 26, 33, 150

# Tombstone box, top-origin
TS_X, TS_Y, TS_W, TS_H = 85, 32, 150, 158
TS_R = TS_W // 2            # dome radius
TS_CX = TS_X + TS_R         # dome center x
TS_DOME_CY = TS_Y + TS_R    # dome center y -- also where the body starts


def _fb(y_from_bottom, height=0):
    """Facade coords are bottom-origin in the design doc; convert to top-origin."""
    return H - y_from_bottom - height


def _lerp(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def _sample_gradient(stops, t):
    """Color at position `t` (0..1) along a multi-stop (t, rgb) gradient."""
    t = max(0.0, min(1.0, t))
    lo, hi = stops[0], stops[-1]
    for i in range(len(stops) - 1):
        if stops[i][0] <= t <= stops[i + 1][0]:
            lo, hi = stops[i], stops[i + 1]
            break
    span = max(1e-6, hi[0] - lo[0])
    return _lerp(lo[1], hi[1], (t - lo[0]) / span)


class Scene:
    def __init__(self, display):
        self.d = display
        self._c = display.color565

    def rgb(self, t):
        return self._c(t[0], t[1], t[2])

    # ---- helpers the driver doesn't provide ----

    def fill_tri(self, x0, y0, x1, y1, x2, y2, color):
        """Scanline triangle. rdagger's fill_polygon is regular-polygon only."""
        pts = sorted(((y0, x0), (y1, x1), (y2, x2)))
        (ya, xa), (yb, xb), (yc, xc) = pts
        if yc == ya:
            return
        for y in range(ya, yc + 1):
            t_long = (y - ya) / (yc - ya)
            x_long = xa + (xc - xa) * t_long
            if y < yb:
                t = 0 if yb == ya else (y - ya) / (yb - ya)
                x_short = xa + (xb - xa) * t
            else:
                t = 0 if yc == yb else (y - yb) / (yc - yb)
                x_short = xb + (xc - xb) * t
            left, right = int(min(x_long, x_short)), int(max(x_long, x_short))
            if right >= left:
                self.d.fill_rectangle(left, y, right - left + 1, 1, color)

    def fill_arch(self, x, y, w, h, color, shoulder=0.34):
        """Pointed (lancet) arch: polygon 0 100%, 0 34%, 50% 0, 100% 34%, 100% 100%."""
        sh = int(h * shoulder)
        self.d.fill_rectangle(x, y + sh, w, h - sh, color)
        self.fill_tri(x, y + sh, x + w // 2, y, x + w - 1, y + sh, color)

    def fill_arch_gradient(self, x, y, w, h, stops, shoulder=0.34):
        """Vertical 3-stop gradient clipped to a lancet arch."""
        top, mid, bot = stops
        sh = int(h * shoulder)
        for row in range(h):
            t = row / max(1, h - 1)
            color = self.rgb(_lerp(top, mid, t / 0.6) if t < 0.6
                             else _lerp(mid, bot, (t - 0.6) / 0.4))
            if row < sh:
                half = int((w / 2) * (row / max(1, sh)))
                if half > 0:
                    self.d.fill_rectangle(x + w // 2 - half, y + row, half * 2, 1, color)
            else:
                self.d.fill_rectangle(x, y + row, w, 1, color)

    def v_gradient(self, x, y, w, h, stops, bands=40):
        """Vertical gradient in horizontal bands. stops = list of (t, rgb),
        `t` relative to this call's own [0, h) span (used for self-contained
        shapes like the tombstone). For a patch that needs to match a larger
        gradient it's embedded in (e.g. a chunk of sky), use
        v_gradient_absolute() instead so `t` lines up with the real
        background rather than restarting at 0 for the patch."""
        step = max(1, h // bands)
        for row in range(0, h, step):
            t = row / max(1, h - 1)
            color = self.rgb(_sample_gradient(stops, t))
            self.d.fill_rectangle(x, y + row, w, min(step, h - row), color)

    def v_gradient_absolute(self, x, y, w, h, stops, total_h, y0=0, bands=40):
        """Like v_gradient(), but `t` is computed from the patch's real
        position within a `total_h`-tall gradient starting at `y0`, not
        reset to 0 at the top of the patch -- for restoring a sub-rectangle
        of a larger gradient so it actually matches its surroundings."""
        step = max(1, h // bands)
        for row in range(0, h, step):
            t = (y + row - y0) / max(1, total_h - 1)
            color = self.rgb(_sample_gradient(stops, t))
            self.d.fill_rectangle(x, y + row, w, min(step, h - row), color)

    # ---- static passes ----

    def draw_all(self):
        self.draw_sky()
        self.draw_facade()
        self.draw_tombstone()
        self.draw_chrome()

    def draw_sky(self):
        self.v_gradient(0, 0, W, H, SKY_STOPS, bands=48)
        for (x, y, c) in ((30, 22, STAR_A), (112, 16, STAR_B), (262, 26, STAR_A)):
            self.d.fill_rectangle(x, y, 1, 1, self.rgb(c))
        # moon: 26px circle centered ~(283, 29), with two dim glow rings
        self.d.fill_circle(283, 29, 22, self.rgb(GLOW_RING_2))
        self.d.fill_circle(283, 29, 17, self.rgb(GLOW_RING_1))
        self.d.fill_circle(283, 29, 13, self.rgb(MOON_EDGE))
        self.d.fill_circle(283, 29, 10, self.rgb(MOON_MID))
        self.d.fill_circle(281, 27, 6, self.rgb(MOON_CORE))

    def draw_facade(self):
        # Every offset here is `_fb(bottom, height)` where `bottom`/`height`
        # are the literal CSS `bottom`/`height` values from panel 1B of the
        # .dc.html source (the authoritative geometry) -- cross-checked by
        # hand against the markup, since several of these were originally
        # transcribed wrong (e.g. the chimney/towers/entry-arch were each
        # shifted 15-56px off, which is why the candlestick and a window used
        # to overlap and most of the facade detail was invisible/mispositioned).
        d = self.d
        sil = self.rgb(SILHOUETTE)
        body = self.rgb(BODY)

        d.fill_rectangle(50, _fb(0, 42), 222, 42, body)

        # iron cresting: 2px bar every 7px along the parapet
        cy = _fb(42, 5)
        for x in range(50, 272, 7):
            d.fill_rectangle(x, cy, 2, 5, sil)

        d.fill_rectangle(108, _fb(38, 16), 7, 16, sil)       # chimney
        d.fill_rectangle(106, _fb(53, 3), 11, 3, sil)        # cap

        # flanking pitched towers: pentagon, peak at 50%, shoulders at 32%
        for x in (46, W - 44 - 36):
            self._pentagon(x, 36, 64, sil)

        # left tall tower + spire (spire: x1,w54,bottom54,h44, apex at top-center)
        d.fill_rectangle(6, _fb(0, 56), 44, 56, sil)
        spire_top = _fb(54, 44)
        self.fill_tri(1, spire_top + 44, 28, spire_top, 55, spire_top + 44, sil)
        d.fill_rectangle(27, _fb(96, 10), 2, 10, sil)
        self._diamond(28, _fb(104, 7) + 3, 3, sil)

        # right tower + spire
        d.fill_rectangle(W - 8 - 40, _fb(0, 50), 40, 50, sil)
        rx = W - 3 - 50
        r_spire_top = _fb(48, 38)
        self.fill_tri(rx, r_spire_top + 38, rx + 25, r_spire_top, rx + 50, r_spire_top + 38, sil)
        d.fill_rectangle(W - 27 - 2, _fb(84, 9), 2, 9, sil)
        self._diamond(W - 27, _fb(91, 6) + 3, 3, sil)

        # window glow halo (two dim rings), then the lit pair
        d.fill_circle(28, _fb(18, 26), 13, self.rgb(GLOW_RING_2))
        d.fill_circle(28, _fb(18, 26), 8, self.rgb(GLOW_RING_1))
        self.fill_arch_gradient(18, _fb(24, 17), 8, 17, WIN_LIT)
        self.fill_arch_gradient(30, _fb(24, 17), 8, 17, WIN_DIM1)
        self.fill_arch_gradient(W - 20 - 8, _fb(20, 16), 8, 16, WIN_DIM2)
        for x in (88, 226):
            self.fill_arch(x, _fb(12, 15), 7, 15, self.rgb(WINDOW_DARK))

        # rose window
        d.fill_circle(161, _fb(31, 15) + 7, 7, self.rgb(ROSE_EDGE))
        d.fill_circle(161, _fb(31, 15) + 7, 4, self.rgb(ROSE_CORE))

        # entry arch + inner glow
        self.fill_arch(151, _fb(0, 26), 20, 26, sil, shoulder=0.34)
        self.fill_arch_gradient(154, _fb(0, 20), 14, 20,
                                ((145, 101, 45), (110, 74, 32), (74, 48, 22)),
                                shoulder=0.34)

        # ground fade
        self.v_gradient(0, _fb(0, 20), W, 20,
                        [(0.0, SKY_BOTTOM), (0.45, SILHOUETTE), (1.0, SILHOUETTE)],
                        bands=10)

    def _pentagon(self, x, w, h, color):
        y0 = _fb(h)
        sh = int(h * 0.32)
        self.d.fill_rectangle(x, y0 + sh, w, h - sh, color)
        self.fill_tri(x, y0 + sh, x + w // 2, y0, x + w - 1, y0 + sh, color)

    def _diamond(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            span = r - abs(dy)
            if span > 0:
                self.d.fill_rectangle(cx - span, cy + dy, span * 2, 1, color)

    def draw_tombstone(self):
        d = self.d
        r, cx = TS_R, TS_CX
        # dome
        d.fill_circle(cx, TS_DOME_CY, r, self.rgb(STONE_TOP))
        # body gradient below the dome
        self.v_gradient(TS_X, TS_DOME_CY, TS_W, TS_H - r,
                        [(0.0, STONE_MID), (1.0, STONE_BOT)], bands=24)
        # blend the dome into the body
        self.v_gradient(TS_X, TS_DOME_CY - 12, TS_W, 12,
                        [(0.0, STONE_TOP), (1.0, STONE_MID)], bands=6)
        # 1px top highlight
        d.fill_rectangle(cx - 20, TS_Y + 1, 40, 1, self.rgb((226, 218, 240)))
        # engraved inner border (approximate: dome ring + two side rules)
        edge = self.rgb(STONE_EDGE)
        d.draw_circle(cx, TS_DOME_CY, r - 6, edge)
        d.fill_rectangle(TS_X + 6, TS_DOME_CY, 1, TS_H - r - 6, edge)
        d.fill_rectangle(TS_X + TS_W - 7, TS_DOME_CY, 1, TS_H - r - 6, edge)
        d.fill_rectangle(TS_X + 6, TS_Y + TS_H - 6, TS_W - 12, 1, edge)
        # static "WAIT TIME" label
        d.draw_text8x8(cx - 36, TS_Y + 20, "WAIT TIME", self.rgb(LABEL_DIM))

    def draw_chrome(self):
        """Title and park label -- static, never redrawn."""
        title = "HAUNTED MANSION"
        x = max(0, (W - len(title) * 8) // 2)
        self.d.draw_text8x8(x, 9, title, self.rgb(TITLE))

    def draw_park_label(self, short_label):
        text = short_label.upper()
        x = max(0, (W - len(text) * 8) // 2)
        self.d.draw_text8x8(x, H - 12, text, self.rgb(PARK_LABEL))

    # ---- patch restore, for dirty rects ----

    def restore(self, rect):
        """Redraw the static background inside `rect` only. Every patch this
        app actually uses (the numeral, the message block, the ghost) sits
        either entirely inside the tombstone or entirely in open sky, so
        those are the two cases handled here -- if a future patch straddles
        the facade too, this needs a third branch for it."""
        x, y, w, h = rect
        if _rect_inside(rect, (TS_X, TS_Y, TS_W, TS_H)):
            self._restore_tombstone_patch(x, y, w, h)
        else:
            self._restore_sky_patch(x, y, w, h)

    def _restore_sky_patch(self, x, y, w, h):
        # Samples the SAME gradient draw_sky() painted, at this patch's real
        # position, so an erased patch blends into its surroundings instead
        # of flashing a mismatched color (that mismatch was the ghost's
        # visible trailing line and the "blinking" as it crossed the screen).
        self.v_gradient_absolute(x, y, w, h, SKY_STOPS, total_h=H, y0=0, bands=max(1, h // 4))

    def _restore_tombstone_patch(self, x, y, w, h):
        """Row-by-row restore that respects the dome's actual circular
        silhouette. A naive rectangular fill here (the original approach)
        painted stone-colored pixels into the corners outside the dome's
        curve -- visible as a grey box around the numeral, since R_NUMERAL
        starts well up inside the dome, not just the straight-sided body."""
        r, cx = TS_R, TS_CX
        for row_y in range(y, y + h):
            if row_y < TS_DOME_CY:
                dy = TS_DOME_CY - row_y
                half = int((r * r - dy * dy) ** 0.5) if dy <= r else 0
                left_edge, right_edge = cx - half, cx + half
                if x < left_edge:
                    self._restore_sky_patch(x, row_y, min(w, left_edge - x), 1)
                if right_edge < x + w:
                    start = max(x, right_edge)
                    self._restore_sky_patch(start, row_y, x + w - start, 1)
                seg_x = max(x, left_edge)
                seg_w = min(x + w, right_edge) - seg_x
                if seg_w > 0:
                    self.d.fill_rectangle(seg_x, row_y, seg_w, 1, self.rgb(STONE_TOP))
            else:
                t = (row_y - TS_DOME_CY) / max(1, (TS_Y + TS_H) - TS_DOME_CY)
                color = self.rgb(_sample_gradient(((0.0, STONE_MID), (1.0, STONE_BOT)), t))
                self.d.fill_rectangle(x, row_y, w, 1, color)


def _rect_inside(inner, outer):
    ix, iy, iw, ih = inner
    ox, oy, ow, oh = outer
    return ix >= ox and iy >= oy and ix + iw <= ox + ow and iy + ih <= oy + oh
