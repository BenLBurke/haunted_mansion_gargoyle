# Handoff: Haunted Mansion gothic TFT display

**Target repo:** `BenLBurke/haunted_mansion_gargoyle` @ `main` (`pico-w/`)
**Target hardware change:** 2.8" SPI TFT, 320x240, 16-bit color (assume ILI9341)

## What this is

A redesign of the Pico W build's screen output. The design reference is
`Haunted Mansion Wait Display.dc.html` in this bundle — an HTML prototype of the intended look and
motion. It is **not** code to port; recreate it natively in `pico-w/src/` following the conventions
already in that tree.

Open the HTML in a browser to see the motion. It shows **two treatments**:

- **Panel 1A ("Full seance")** — the visual north star. Multi-layer translucent fog, three bats, two
  ghosts, a hitchhiking trio, twin candelabra. **Not the implementation target** — it needs per-frame
  full-frame alpha compositing.
- **Panel 1B ("Thrifty haunt")** — **this is the target.** Same world, drawn once at boot, with only
  small regions ever redrawing.

**Fidelity: high.** Colors and coordinates below are authoritative.

---

## THE HEADLINE CHANGE: the display is no longer monochrome framebuf

`pico-w/src/` today is built around an SSD1306: I2C, 128x64, 1-bit, and `framebuf.FrameBuffer`
primitives. Specifically:

- `display.py::make_display()` constructs `SSD1306_I2C(width, height, i2c, addr)` over
  `machine.I2C`.
- `renderer.py` and `animations.py` take an `fb` and call `framebuf` methods — `fill`, `text`,
  `rect`, `ellipse`, `poly`, `line` — with `color=1`/`bg=0`.
- The whole screen is repainted every update (`fb.fill(0)` then redraw, then `device.show()`), which
  is free on a 1KB monochrome buffer.
- `big_digits.py` draws 7-segment numerals from rectangles because there's no font asset.

None of that survives the move to a color SPI TFT:

| | Current (SSD1306) | New (ILI9341) |
|---|---|---|
| Bus | I2C @ 400kHz | SPI @ 40MHz |
| Geometry | 128x64 | 320x240 |
| Depth | 1-bit, `color=1` | RGB565, `color565(r,g,b)` |
| Buffer | full `framebuf` in RAM (1KB), `.show()` | **no full buffer** — 153,600 bytes vs 264KB total SRAM, and WiFi/TLS needs 40-50KB during a request |
| Paint model | clear-and-redraw everything | **draw once at boot, then dirty rects only** |
| Primitives | `framebuf` methods | driver methods (`fill_rectangle`, `fill_circle`, `block`, ...) |

**Do not allocate a 320x240 framebuffer.** That is the one hard constraint. `fill(0)` + full redraw is
no longer viable; adopt the dirty-rect model below.

### Recommended driver

`rdagger/micropython-ili9341` (`ili9341.py`). Copy it into `pico-w/src/lib/` alongside the existing
vendored `requests.py` and `ssd1306.py` — same pattern, and the README's vendoring table should gain a
row for it.

Note its primitive set differs from `framebuf`: it has `fill_rectangle`, `fill_circle`, `fill_ellipse`,
`draw_line`, `block`, `draw_text8x8`, and `color565`, but **`fill_polygon` draws regular polygons only**
(sides/radius), not arbitrary vertex lists. The facade needs triangles (spires) and pointed arches, so
include a scanline triangle helper — see `reference/scene.py` in this bundle.

---

## What stays untouched

Your separation of concerns holds up well here. Do **not** modify:

- `state.py` — `StateTracker`, `Snapshot`, `Reactions`, phase logic. Already exactly the state model
  this design needs.
- `parks.py` — `short_label` already yields `"Disneyland"` / `"Magic Kingdom"`, which is precisely the
  footer copy the design calls for.
- `themeparks_api.py` — unchanged.
- `candle.py` — this is the **physical** candlestick LED on PWM. Unrelated to the on-screen candle
  flame, which is new. Keep both; they should flicker independently (the design's screen flame is a
  4-step 1.6s loop, deliberately coarser than the LED's random walk).
- `audio.py`, `network_setup.py`, `wifi_portal.py`, `provision.py`, `gargoyle_config.py` (logic).
- `main.py`'s loop structure — see the small diff noted below.

## What changes

| File | Change |
|---|---|
| `src/lib/ili9341.py` | **new** — vendored driver |
| `src/display.py` | `make_display()` builds SPI + ILI9341 instead of I2C + SSD1306. `Screen` keeps its exact public interface (`show_snapshot`, `show_message`, `play_wait_time_change_animation`) plus one addition, `tick()`. |
| `src/scene.py` | **new** — draws the static gothic mansion once at boot, and redraws small background patches under moving elements |
| `src/renderer.py` | rewritten for color + dirty rects; `render_snapshot` no longer clears the screen, and adds a stale indicator |
| `src/main.py` | three edits — see `reference/main.py.diff` |
| `src/animations.py` | rewritten: lightning strike, numeral roll, drifting ghost, screen candle flame |
| `src/big_digits.py` | **keep the module, restyle the glyphs.** See "Typography" — 7-segment reads as a calculator, not a tombstone. |
| `src/gargoyle_config.py` | new SPI pin keys, drop I2C display keys |
| `config.example.json` | same |
| `docs/HARDWARE.md` | new wiring table for the TFT |
| `pico-w/README.md` | update the vendoring table and the `display_enabled=false` section |
| `tests/` | `test_big_digits.py` needs updating if glyph geometry changes. Everything else is unaffected — the portable-logic suite doesn't touch the display. |

### `main.py` diff

Two changes only:

1. After constructing `screen`, call `screen.begin()` once to paint the static scene.
2. In the main loop, alongside `candle.step()`, add `screen.tick()` — this advances the on-screen flame
   flicker and the occasional ghost drift. It must be cheap and non-blocking (the flame rect is
   14x16x2 = 448 bytes of SPI traffic, and only every ~400ms).

`ConsoleScreen` needs matching no-op `begin()` and `tick()` so `display_enabled: false` still works.

---

## Architecture: dirty rects

Paint the static scene once, then only ever redraw these:

| Region | Rect (x, y, w, h) | When |
|---|---|---|
| Wait numeral | (118, 66, 84, 88) | on `reactions.wait_time_changed` |
| Status message | (97, 76, 126, 62) | on status change, and every 4.2s while `DOWN` |
| On-screen candle flame | (16, 186, 14, 16) | every ~400ms, 4-step loop |
| Ghost | 26x33 window at current x, y=150 | one pass every ~150-210s |
| Lightning | full screen | on `reactions.wait_time_changed` |

To restore under a moving element, call back into `scene.py` to redraw just that patch procedurally —
same drawing code, clipped. This keeps the repo's "no sprite assets" philosophy (as
`animations.py` and `big_digits.py` already state explicitly) and avoids shipping a 150KB `bg.raw`.

*Fallback:* if procedural patch-redraw proves too slow or fiddly, bake the static scene to a
320x240 RGB565 raw file on flash (153,600 bytes) and `seek()` slices out of it instead. Ask the
designer for the export — but try procedural first; it matches the codebase.

---

## The design

### Background
Radial gradient, `ellipse 120% 90% at 50% 108%`: `#332045` 0% -> `#1b1226` 44% -> `#0c0813` 100%. A
vertical linear approximation (`#0c0813` at y=0 to `#332045` at y=240), drawn as ~40 horizontal bands,
is acceptable on a 16-bit panel.

Three stars, 1px, at (30,22), (112,16), (262,26) — `#cfc6b4`, `#b8afc9`, blended to ~50% over the sky.

Moon: 26px circle centered approx (283, 29). Radial `#f6e6c4` -> `#d8bf94` at 62% -> `#a68b62`. Fake the
glow with two or three concentric dim rings (`#2a1f35`-ish) rather than a real blur.

### Gothic facade
Bottom 116px. Silhouette `#0a0610`; main body block `#0b0711`. **Coordinates below are from the bottom
of the panel** unless noted.

- Main hall: x 50, 222 wide, 42 tall
- Iron cresting on the parapet: x 50, y 42, 222x5 — a 2px vertical bar every 7px
- Chimney: x 108, 7x16 at y 38; cap 11x3 at x 106, y 53
- Two flanking pitched towers, pentagon (peak at 50% of top edge, shoulders at 32% height): x 46 and
  right 44, each 36 wide x 64 tall
- Left tall tower: body x 6, 44x56; spire triangle x 1, 54 wide x 44 tall from y 54; mast 2x10 at
  x 27, y 96; diamond finial 7x7 at x 24.5, y 104
- Right tower: body right 8, 40x50; spire triangle right 3, 50x38 from y 48; mast 2x9 at right 27,
  y 84; diamond finial 6x6 at right 24.5, y 91
- Lancet windows — pointed arch, polygon `0 100%, 0 34%, 50% 0, 100% 34%, 100% 100%`:
  - lit, 8x17 at x 18, y 24 — vertical `#ffd08f` -> `#e0902f` @60% -> `#94571c`
  - dim, 8x17 at x 30, y 24 — `#a06c2e` -> `#5b3514` -> `#38200c`
  - dim, 8x16 at right 20, y 20 — `#c9873a` -> `#7e4d1c` -> `#4a2c10`
  - dark, 7x15 at x 88 and x 226, y 12 — `#050309`
  - glow halo around the lit pair: 26px circle at x 15, y 18, `rgba(255,190,105,0.45)` -> transparent
    at 70%; approximate with two dim rings
- Rose window: 15px circle at x 154, y 31 — `#e09b41` -> `#6d4116` @58% -> `#0a0610`
- Entry arch: pointed arch 20x26 at x 151, y 0 in `#0a0610`; inner glow arch 14x20 at x 154, y 0,
  vertical `rgba(242,169,75,0.6)` -> `rgba(140,84,28,0.3)`
- Ground fade: bottom 20px, transparent -> `#0a0610` at 45%

### On-screen candlestick
Approx x 8-28, from 46px up the bottom, rising 40px. Offsets local to that box, bottom-up:

- base 12x3.4 ellipse at x 4 — `#6b5330` -> `#241a10`
- knop 4.8x2.4 ellipse at x 7.6, y 2.6
- brass stem 2.8x12 at x 8.6, y 4 — horizontal `#1e150d` / `#7d6136` @45% / `#2a1f14`
- mid knop 7.2x3.6 ellipse at x 6.4, y 9
- drip pan 9.2x3 at x 5.4, y 15 — `#8a6b3a` -> `#33260f`
- wax body 6x10 at x 7, y 17.6 — horizontal `#8d8069` / `#f4ecd7` @42% / `#a2957c`
- wax run 1.8x5 at x 6.6, y 20.6 — `#efe6cf`
- static halo, 18px circle at x 1, y 23 — bake it into the static pass
- **flame** 2.8x7.4 at x 8.6, y 27.2 — vertical `#fffbee` -> `#ffc871` @46% -> `#f0742a`

Flame animation: **4 discrete steps, 1.6s loop.** Steps scale/rotate about the base:
(1.00x1.00, -1.5deg), (0.86x1.22, +2deg), (1.12x0.88, -2.5deg), (0.94x1.14, +1deg). Deliberately
stepped — it's the cheapest continuous motion on the panel. Draw as 4 hardcoded flame outlines.

### Tombstone (the hero)
Centered, 32px from the top: 150x158 at x 85. Semicircular top on a rectangular base — radius
`74 74 5 5`. Fill: vertical `#645c6c` 0% -> `#443e4d` 48% -> `#302b39` 100%. Top highlight 1px
`rgba(226,218,240,0.22)`. Engraved inner border: inset 6px, 1px `rgba(226,218,240,0.14)`.

- `WAIT TIME` — 20px down from the stone's top, centered, 8px, weight 600, tracking 0.28em, `#b8afc0`.
  Static.
- **Numeral** — centered in an 88px band starting 34px down from the stone's top. 66px, weight 900,
  `#ffd79a`.
- **Unit** — 16px up from the stone's bottom, centered, 9px, weight 600, tracking 0.3em, `#d8ceb8`.
- Non-operating states replace numeral + unit with a centered wrapped message, inset 12px, 12px type,
  line-height 1.5, `#e2d6bd`.

### Ghost
26x33, drifting horizontally at y 150 (from the top). Radial `rgba(226,218,240,0.55)` fading out at
66%, shaped `52% 52% 40% 40%`. Two eyes, 3x4, `#241a33`, at local (7,12) and (15,12).

On an ILI9341 with no alpha, approximate: fill the body in a mid spectral `#8d86a3`, ring it with a
dimmer `#4a4459`, and let the eyes read as holes. Your existing `_ghost_frame()` in `animations.py`
already has the right silhouette instinct (dome + torso + scalloped hem) — carry that shape over.

### Park label
4px up from the bottom, centered, 8px, tracking 0.2em, `#a99cb8`. Static — `park.short_label.upper()`.

---

## Behavior

Everything is driven by the `Reactions` object `StateTracker.update()` already returns.

**Lightning** — fires **only** on `reactions.wait_time_changed`, never on a timer. Double-strike
stutter, 900ms total: opacity 0 -> 0.92 @4% -> 0.05 @10% -> 0.75 @16% -> 0.02 @24% -> 0.45 @34% -> 0.
That stutter is the whole character; keep it.

On device: `fill_rectangle` the full panel near-white (`#fffcf0`), hold ~60ms, repaint the static scene,
hold ~70ms, repeat dimmer, restore. Roughly 150ms per full push at 40MHz — fine for a once-a-minute
event, and it reads as a flicker. This replaces the current
`play_wait_time_change_animation()` bat-then-ghost sting, which at 20+20 frames x 80ms blocks for 3.2
seconds — too long on a panel this size, and the ghost now has its own independent schedule.

**Numeral roll** — 480ms, `cubic-bezier(.2,.8,.2,1)`: translateY +26 -> 0, scale 0.94 -> 1.0. On device,
drop the scale and blur; step translateY over ~8 frames within the numeral rect, redrawing the
background patch each frame.

**Spectral cadence — IMPORTANT.** The user explicitly wants a near-still panel: **one ghost pass roughly
every 2.5-3.5 minutes, then nothing.** Schedule it (`next_ghost = now + randint(150, 210)`), run the
pass over ~4s, go idle. Only the flame flickers continuously. This is a deliberate reversal of the
current design, where the animation fires on every wait change.

**Status handling.** `renderer.py`'s `STATUS_LABELS` currently maps five statuses; the design's copy
covers three. Map the rest:

| `attraction.status` | Display |
|---|---|
| `OPERATING` | the numeral + unit |
| `CLOSED` | `Closed` |
| `DOWN` | alternate the two spook messages every 4.2s |
| `REFURBISHMENT` | `Unavoidably detained by pranky spirits` (it fits the fiction better than "REFURB") |
| `UNKNOWN` | `Lost the signal...` — reuse the existing wording from `main.py` |

**Fetch failure — DECIDED: keep the last known number.** `main.py` currently calls
`screen.show_message("Lost the signal...", "retrying")`, which wipes the number. **Change this.** On a
`ThemeParksApiError`, leave the numeral exactly as it is and draw only a small stale indicator; never
blank the tombstone. The number stays until a successful fetch replaces it — a stale wait time is far
more useful on an always-on ambient display than an error message, and the panel should never look
broken.

Concretely, in `_poll_and_react`:

```python
except ThemeParksApiError as exc:
    print("themeparks.wiki request failed:", exc)
    screen.show_stale()   # NOT show_message() -- leaves the numeral untouched
    return
```

Add `show_stale()` / `clear_stale()` to `Screen` (and no-op prints on `ConsoleScreen`). The indicator
should be quiet and in-fiction rather than an error chrome: a small dim `#a99cb8` glyph in the top-left
corner, roughly 8x8 at (8, 9), mirroring where the existing `connected` flag already draws its `"!"`.
An unlit-candle or small dim moon reads better than a warning triangle. Clear it on the next successful
fetch.

This also means the boot sequence needs care: `screen.show_message("Waking up...")` before the first
poll is still correct, since there is no last-known value yet. Only suppress the wipe once at least one
successful fetch has landed — track that with a `has_data` flag, or just check
`tracker.current is not None`, which `StateTracker` already exposes.

**Do not** persist the last value across a reboot. After `machine.reset()` the number could be hours
stale with no way to signal that, so boot should show `Waking up...` and wait for a real fetch.

**999 easter egg** — when `wait_minutes >= 999`, the unit label becomes `AN ETERNITY`.

---

## Copy (exact strings)
- Title: `HAUNTED MANSION`
- Above the number: `WAIT TIME`
- Unit: `MINUTES` / `MINUTE` (when 1) / `AN ETERNITY` (when >= 999)
- Closed for the day: `Closed`
- Down, message A: `Playful spooks have interrupted the tour`
- Down, message B: `Unavoidably detained by pranky spirits`
- Footer: `DISNEYLAND` / `MAGIC KINGDOM`

Note the current `renderer.py` shows `MIN WAIT` and park hours; the design shows `MINUTES` and no
hours. Park hours are still fetched and still drive the open/close audio cues — they're just no longer
on screen. Confirm that's intended before deleting `_hours_text()`.

---

## Typography

The design uses Cinzel (numerals, labels) and Cinzel Decorative (title) — Victorian serifs. Neither
exists on the Pico, and `draw_text8x8` won't carry a 66px hero numeral.

`big_digits.py`'s 7-segment glyphs are the right *idea* (procedural, no asset) but the wrong *voice* —
they read as a calculator, and the whole point of the tombstone is that the number looks engraved.
**Restyle the glyph geometry** in place, keeping the module's `draw_number` / `measure` API:

- give each stroke a slab serif — a 2px cap block at each terminal
- vary stroke weight: vertical stems ~8px, horizontals ~6px at 66px tall
- true curved bowls on `0 3 6 8 9` via `fill_circle` arcs rather than segment rectangles

Alternative if that proves fiddly: convert Cinzel weight 900 at 66px to a bitmap font containing
**only the ten digits** (`font_to_py`). Ten glyphs is a small footprint. This breaks the "no font
asset" convention, so it's the designer's call — worth asking.

Static text (title, `WAIT TIME`, unit, park label) can stay `draw_text8x8` at 1x/2x, or be drawn once
as part of the static pass. It never changes, so cost is irrelevant.

---

## Config changes

Remove: `i2c_id`, `i2c_scl_pin`, `i2c_sda_pin`, `display_i2c_address`.
Add (values are suggestions — verify against the actual wiring):

```json
"spi_id": 0,
"spi_baudrate": 40000000,
"spi_sck_pin": 18,
"spi_mosi_pin": 19,
"spi_cs_pin": 17,
"spi_dc_pin": 15,
"spi_rst_pin": 14,
"spi_backlight_pin": 13,
"display_width": 320,
"display_height": 240,
"display_rotation": 90
```

Keep `display_width`/`display_height`/`display_enabled` — the names carry over. `gargoyle_config.py`'s
defaults and `test_config.py` both need updating.

---

## Design tokens

- Sky: `#0c0813`, `#1b1226`, `#332045`
- Silhouette: `#0a0610`, `#0b0711`, `#050309`
- Amber: `#f2a94b` (accent), `#ffd79a` (numeral), `#ffc871`, `#f0742a`, `#fffbee`, `#ffd08f`,
  `#e0902f`, `#94571c`, `#c9873a`, `#7e4d1c`, `#4a2c10`
- Brass: `#8a6b3a`, `#7d6136`, `#6b5330`, `#33260f`, `#241a10`, `#2a1f14`, `#1e150d`
- Wax: `#f4ecd7`, `#efe6cf`, `#a2957c`, `#8d8069`
- Stone: `#645c6c`, `#443e4d`, `#302b39`
- Bone/text: `#e7dcc6`, `#e2d6bd`, `#d8ceb8`, `#b8afc0`, `#a99cb8`
- Moon: `#f6e6c4`, `#d8bf94`, `#a68b62`
- Spectral: body `#8d86a3`, edge `#4a4459`, eyes `#241a33`

Type scale (px): 66 numeral w900 / 13 title w700 ls .24em / 12 message / 9 unit w600 ls .3em /
8 `WAIT TIME` + park w600 ls .2-.28em.

---

## Files in this bundle

- `Haunted Mansion Wait Display.dc.html` — the design reference. Open in a browser. **Panel 1B** is the
  target; 1A is the north star. (`support.js` is only needed for that file to render.)
- `reference/scene.py` — static mansion draw + background patch restore, written against rdagger's
  ILI9341 API, with the scanline triangle/arch helpers the driver lacks
- `reference/renderer_tft.py` — numeral, unit label, message block, and the stale indicator; nothing
  clears the screen
- `reference/display_tft.py` — `Screen` preserving your existing public interface, plus `begin()`,
  `tick()`, `show_stale()`, `clear_stale()`
- `reference/animations_tft.py` — lightning, numeral roll, ghost drift, flame flicker
- `reference/main.py.diff` — the three edits needed in `main.py`, as a diff
- `reference/config.additions.json` — the config delta above
- `reference/tools/preview.py` — desktop harness: fakes the ILI9341 API with Pillow so the scene renders
  to a PNG on a laptop, with real 5-6-5 color quantization. **Start here.**
- `TESTING.md` — how to validate all of this without hardware, and in what order

The `reference/` modules are **starting points, not finished code** — they encode the geometry and the
dirty-rect discipline so nobody has to re-derive it from CSS. Fold them into `pico-w/src/` under the
repo's existing naming.

## Open questions

1. Is the 2.8" module actually ILI9341? ST7789 and ILI9488 are both common at that size and need a
   different driver. Confirm before writing the pin map.
2. ~~Keep the last good number on a fetch failure?~~ **Decided: yes.** See "Fetch failure" above.
3. Drop park hours from the screen entirely (the design has no room for them)?
4. Restyle `big_digits.py` procedurally, or ship a 10-glyph Cinzel bitmap font?
5. The gothic facade eats the bottom 116px of 240. The design was drawn for it, but it's a lot of
   screen given the number is the hero — worth a look on real hardware before committing.
