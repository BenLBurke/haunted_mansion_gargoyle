# How to test this before it's on hardware

Four layers, cheapest first. You can do the first three today with no TFT wired.

---

## 1. The HTML mock (zero setup)

`Haunted Mansion Wait Display.dc.html` — open in a browser. Panel 1B cycles live through
25 → 45 → 70 min, a down state, the 999 eternity egg, and Closed, firing lightning on each change.
Use the Tweaks panel to force a specific wait, status, or park.

This is the reference for *intent* only. It will always look better than the panel — real alpha, real
fonts, sub-pixel positioning. Judge composition and pacing here, not fidelity.

---

## 2. Desktop preview of the actual device code (the important one)

`reference/tools/preview.py` fakes rdagger's `Display` API with Pillow, so `scene.py`,
`renderer_tft.py`, and `animations_tft.py` render to a PNG on your laptop. This is how you iterate on
geometry without reflashing.

```
cd pico-w
pip install pillow
mkdir -p tools && cp <handoff>/reference/tools/preview.py tools/
python -m tools.preview
```

Then check each state:

```
python -m tools.preview --wait 5 --out t-1digit.png
python -m tools.preview --wait 45 --out t-2digit.png
python -m tools.preview --wait 120 --out t-3digit.png     # digit box narrows here
python -m tools.preview --wait 999 --out t-eternity.png   # AN ETERNITY label
python -m tools.preview --status CLOSED --out t-closed.png
python -m tools.preview --status DOWN --out t-down.png    # longest string, worst wrap case
python -m tools.preview --status REFURBISHMENT --out t-refurb.png
python -m tools.preview --stale --out t-stale.png
python -m tools.preview --park "Magic Kingdom" --out t-wdw.png
python -m tools.preview --ghost 150 --out t-ghost.png     # ghost over the facade
for i in 0 1 2 3; do python -m tools.preview --flame $i --out t-flame-$i.png; done
```

Two things it gets genuinely right, which is why it's worth the setup:

- **`color565()` quantizes to real 5-6-5 and unpacks back.** Banding in the sky gradient and the
  tombstone shows up in the PNG exactly as it will on the panel. This is the single biggest risk in the
  design — a purple-to-black gradient across 240px in 16-bit color is where banding lives.
- **It counts primitives and pixels touched.** `scene.draw_all()` runs once at boot so its cost is
  irrelevant, but if a *dirty-rect* path reports a large pixel count, that's a bug you want to see
  before it's a stutter on hardware.

What it does **not** tell you: real SPI timing, real `draw_text8x8` glyph shapes (Pillow's default font
stands in), or how the amber reads on a physical backlight.

### What to look for
- Does the 3-digit numeral still fit and stay centered? That's the tightest layout case.
- Does the `DOWN` message wrap to 2 lines inside the stone without touching the engraved border?
- Is the ghost legible against the facade silhouette? It's `#8d86a3` over `#0a0610` — should be, but
  it crosses the lit windows.
- Sky banding. If it's ugly, add dithering or reduce the gradient's range.

---

## 3. Your existing pytest suite

Unaffected by any of this — `state.py`, `parks.py`, `themeparks_api.py`, and `candle.py` don't change.

```
cd pico-w && pytest
```

Two tests will need updating as you go:
- `test_config.py` — the config keys change (I2C out, SPI in)
- `test_big_digits.py` — if you restyle the glyph geometry

Worth **adding**: `unit_label()` from `renderer_tft.py` is pure and covers the 1 / plural / 999 branches,
and `renderer_tft._wrap()` is pure too. Both are exactly the dependency-free, testable-under-CPython
shape the rest of your suite already follows.

---

## 4. On the Pico, before the TFT is wired

Your `display_enabled: false` console path still works — I kept `ConsoleScreen` with matching
`begin()` / `tick()` / `show_stale()` no-ops. So you can flash and validate WiFi, provisioning, polling,
audio, and the physical candle LEDs with no panel attached:

```json
"display_enabled": false
```

```
mpremote connect auto
```

You'll see the familiar lines, plus the new ones:

```
[screen] (static mansion scene would be painted here)
[screen] Disneyland: 22 min wait (connected=True)
[screen] (lightning strike would play here)
[screen] (fetch failed -- keeping last known number, stale mark on)
```

**Test the stale path deliberately** — it's the behavior you just decided on and the easiest to get
wrong. Point `API_URL` at a dead host, or pull the router, and confirm you see the stale line and
*not* `Lost the signal...` (that should only appear before the very first successful fetch).

---

## 5. Once the panel is wired

Order matters:

1. **Confirm the controller first.** Run a bare `display.clear()` then a red `fill_rectangle`. If
   nothing or garbage appears, it's likely ST7789 or ILI9488, not ILI9341 — different driver, and
   everything downstream is wasted effort until that's settled.
2. **Check rotation and origin.** Many 2.8" modules are natively 240×320 portrait; `rotation=90` gets
   you 320×240 landscape, but the direction varies by board. If the mansion is upside down, that's all
   this is.
3. **Time `scene.draw_all()`.** Wrap it in `ticks_ms`. Under ~400ms is fine for a once-at-boot cost. If
   it's multiple seconds, the gradient band count is too high — raise the `bands` step.
4. **Time `lightning()`.** Six full-screen pushes. If it feels sluggish rather than snappy, cut to two
   strikes or lower the hold times.
5. **Watch it idle for ten minutes.** This is the real acceptance test: the panel should look
   essentially still, with just the flame flickering, and exactly one ghost pass. If you notice motion
   more often than that, the cadence is wrong.

---

## Suggested order of work

1. Copy `preview.py` in, get `scene.draw_all()` rendering a PNG. Iterate on the facade until it looks
   right at 2× — this is where most of the design risk lives, and it's the cheapest place to fix it.
2. Get the numeral and all message states looking right in the preview.
3. Only then vendor the driver, change the config, and flash.
4. Wire the panel last.
