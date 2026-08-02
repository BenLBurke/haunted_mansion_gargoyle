# haunted_mansion_gargoyle -- Pico W build

A MicroPython rewrite of the [Pi Zero build](../pi-zero/) for the Raspberry
Pi Pico W: cheaper, lower power, instant-on, no SD card or Linux to
maintain -- at the cost of everything Linux gives you for free (systemd,
NetworkManager, a real filesystem, `pip`). Feature set is the same:

- Each candlestick's LED flickers like a real candle flame (PWM).
- A small OLED screen shows the current Haunted Mansion wait time.
- A ghost/bat animation plays across the screen whenever the wait changes.
- A speaker dings when the wait goes down, and plays a cue when the park
  opens and closes for the day (I2S -- the Pico has no analog audio out).
- A self-hosted captive portal handles first-time WiFi setup from a phone,
  no keyboard/monitor needed.
- Hold a physical reset button to forget WiFi and go back into setup mode
  (also lets you pick a different park).
- Checks for and installs new releases on its own, with automatic rollback
  if an update doesn't come up healthy -- see [docs/OTA.md](docs/OTA.md).

See [docs/HARDWARE.md](docs/HARDWARE.md) for the bill of materials, wiring,
and flashing/deployment steps, and [docs/WIFI_SETUP.md](docs/WIFI_SETUP.md)
for the setup flow.

## Why this is a separate implementation, not a port

The Pi Zero build runs CPython on Linux and leans on Flask, Pillow,
`requests`, `gpiozero`, `luma.oled`, NetworkManager, and systemd. None of
that exists on a bare RP2040 running MicroPython -- there's no OS
underneath. Everything here is written against MicroPython's own
`machine`/`network`/`framebuf`/`asyncio` APIs instead:

| | Pi Zero | Pico W |
|---|---|---|
| HTTP client | `requests` | vendored `requests.py` from micropython-lib (`lib/requests.py`) |
| OLED | Pillow + `luma.oled` | `framebuf` + vendored `ssd1306.py` (`lib/ssd1306.py`) |
| Big wait-time number | Pillow bitmap font | hand-drawn chunky 7-segment digits (`big_digits.py`) -- no font asset needed |
| Sound playback | `aplay` over ALSA | raw WAV parsing + `machine.I2S` streaming (`audio.py`) |
| WiFi provisioning | NetworkManager hotspot + Flask + dnsmasq redirect | `network.WLAN` AP mode + hand-rolled DNS spoofing + `asyncio` HTTP server (`wifi_portal.py`) |
| Config | YAML | JSON (`gargoyle_config.py`) -- MicroPython has no PyYAML |
| Process supervision | systemd | crash-and-reset in `main.py` (see docs/HARDWARE.md for why there's no hardware watchdog) |
| Reset button | `gpiozero.Button` (hold-time built in) | hand-rolled hold-duration detection (`reset_button.py`) |
| OTA updates | git clone + systemd timer, health-checked from outside the app process (`scripts/ota_apply.py`) | verified download + backup/swap + `boot.py`-based rollback (`ota.py`, `boot.py`) -- see [docs/OTA.md](docs/OTA.md) |

`state.py`, `parks.py`, and the wait-time-formatting/flicker-math logic are
kept dependency-free on purpose so they read almost identically to their
Pi-side counterparts and can be unit tested the same way.

## Developing without the hardware

The device-only modules (`display.py`, `candle.py`'s hardware factory,
`audio.py`'s I2S bits, `network_setup.py`, `wifi_portal.py`) import
`machine`/`network` at call time, not at module level, so they can't run
off-device -- but everything else can. Run the portable-logic test suite
from this directory:

```
python3 -m venv venv && source venv/bin/activate
pip install pytest
pytest
```

This covers wait-time parsing/formatting, wait-time/park-open change
detection, the candle flicker algorithm, config loading, the park registry,
reset-button hold-duration detection, and the OTA updater's file-swap and
rollback logic (`ota.py`/`boot.py`, verified against a real MicroPython
interpreter too, not just CPython) -- the same scope of coverage as the Pi
Zero build's tests, minus whatever genuinely needs real hardware or a real
network stack to exercise.

## Testing without the screen or speaker

Bringing this up on a breadboard before the OLED/amp are wired? Set these in
`config.json`:

```json
"display_enabled": false,
"audio_enabled": false,
```

With those off, the app prints what it *would* have shown/played to the
serial console instead of touching the OLED or I2S -- connect with
`mpremote connect auto` or Thonny's Shell and you'll see lines like:

```
[screen] Disneyland: 22 min wait (9:00am-11:00pm) (connected=True)
[screen] (ghost/bat animation would play here)
[sound] wait_decreased
```

This isn't optional cosmetics: without an OLED actually on the I2C bus, a
write with nothing there to ACK it raises `OSError` and crashes `main.py` at
boot. Candle LEDs and WiFi aren't affected either way -- PWM and I2S don't
need anything listening on the other end, so those work identically whether
or not you've wired the rest yet. Flip `display_enabled`/`audio_enabled`
back to `true` once each part is actually wired.

## Sound cues

Reuses the Pi Zero build's tone generator rather than duplicating it --
MicroPython has no `wave` module to synthesize WAVs on-device anyway, so
generate them once on a PC:

```
cd ../pi-zero
python -m gargoyle.audio.generate_tones
```

That writes into `pi-zero/gargoyle/audio/sounds/`. Copy those `.wav` files
to this project's `pico-w/sounds/` (gitignored, same as the Pi Zero side)
and then onto the Pico's flash under `/sounds/` -- see
[docs/HARDWARE.md](docs/HARDWARE.md). Both builds use the same format
(22050Hz mono 16-bit), so the files are interchangeable. Drop your own
recording in with a matching filename to replace any cue.
