# haunted_mansion_gargoyle

A 3D-printed gargoyle holding two candlesticks that sits on your desk and
haunts you with live Haunted Mansion wait times from Disneyland or Walt
Disney World.

- Each candlestick has an LED that flickers like a real candle flame.
- A small OLED screen embedded in the print shows the current wait time.
- A ghost/bat animation plays across the screen whenever the wait time changes.
- A speaker dings ominously when the wait goes down, and plays a cue when
  the park opens and closes for the day.
- No keyboard or monitor needed to set it up -- on first boot (or if it ever
  loses its WiFi) it broadcasts its own hotspot with a captive setup page so
  you can hand it your home WiFi from a phone.
- Hold a physical reset button to forget WiFi and go back into setup mode
  (also lets you pick a different park).
- Checks for and installs new releases on its own, with automatic rollback
  if an update doesn't come up healthy -- see [docs/OTA.md](docs/OTA.md).

It runs on a Raspberry Pi Zero 2 W (or Zero W) embedded in the print,
polling the community [themeparks.wiki](https://themeparks.wiki/) API.

## Hardware

See [docs/HARDWARE.md](docs/HARDWARE.md) for the bill of materials, GPIO
wiring diagram, and notes on integrating the LEDs/screen/speaker into the
3D print itself.

## Setup

1. Flash Raspberry Pi OS Lite (Bookworm+) to a microSD card and boot the Pi.
2. Wire up the hardware per [docs/HARDWARE.md](docs/HARDWARE.md).
3. Run the installer -- it clones this repo itself (into `/opt/gargoyle`,
   pinned to the latest tagged release), so you don't need to `git clone`
   it yourself first:
   ```
   curl -fsSL https://raw.githubusercontent.com/BenLBurke/haunted_mansion_gargoyle/main/pi-zero/scripts/install.sh | sudo bash
   ```
4. Connect it to your WiFi -- see [docs/WIFI_SETUP.md](docs/WIFI_SETUP.md).

From here it checks for and applies new releases on its own -- see
[docs/OTA.md](docs/OTA.md) -- and a long-press on the reset button forgets
WiFi and re-enters setup mode any time you need to reconfigure it.

Configuration (which park to track, GPIO pin assignments, sound cues, poll
interval, etc.) lives in `/etc/gargoyle/config.yaml`; edit it and
`sudo systemctl restart gargoyle` to apply changes. See
[config/config.example.yaml](config/config.example.yaml) for every option.

## How it decides what to show

Every `poll_interval_seconds` (default 60s) it fetches the Haunted Mansion's
live status and the park's hours for the day from themeparks.wiki, and reacts
to what changed since the last check:

| Change | Screen | Speaker |
|---|---|---|
| Wait time changes at all | ghost/bat animation, then the new number | -- |
| Wait time goes down | (as above) | ding (`sound_on_wait_decrease`) |
| Wait time goes up | (as above) | off by default (`sound_on_wait_increase`) |
| Park opens for the day | -- | chime (`sound_on_park_open`) |
| Park closes for the day | "Closed for the day" | howl (`sound_on_park_close`) |

The candle LEDs flicker continuously regardless of any of the above.

## Developing without the hardware

Every hardware-facing module (GPIO LEDs, the OLED, ALSA audio) has a mock
fallback so you can run and test the app on a regular machine:

```
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
python -m gargoyle.main --simulate
```

In `--simulate` mode the "screen" is written to `/tmp/gargoyle_screen.png`
after every frame, LEDs/audio just log what they would have done, and WiFi
provisioning is skipped entirely.

Run the test suite (covers the API client, wait-time/park-open change
detection, the candle flicker algorithm, config loading, and the OTA
updater's apply/rollback logic -- the parts that don't need real hardware
to exercise):

```
pytest
```

## Sound cues

`gargoyle/audio/generate_tones.py` synthesizes placeholder WAV files for
each cue (startup, wait-time ding, park open, park close "howl") from pure
math -- no binary assets needed in the repo. Drop your own recording into
`gargoyle/audio/sounds/<cue>.wav` (matching filenames from that script) to
replace any of them; the app prefers whatever's already there and only
generates a cue if the file is missing.

## Attribution

Wait times and schedule data come from the free, community-run
[themeparks.wiki](https://themeparks.wiki/) API. It's not affiliated with
Disney; be a good citizen and don't poll faster than `poll_interval_seconds`
needs to be.
