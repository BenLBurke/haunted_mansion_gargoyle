# Hardware (Pico W)

## Bill of materials

| Part | Notes |
|---|---|
| Raspberry Pi Pico W (or Pico 2 W) | Needs the "W" -- plain Pico has no WiFi radio |
| SSD1306 OLED, 128x64, I2C | Same panel as the Pi Zero build |
| 2x 5mm LEDs, warm/amber or "flicker flame" tint | One per candlestick |
| 2x 220-330Ω resistors | Current limiting for the LEDs |
| MAX98357A I2S 3W Class-D amp breakout | The Pico has no analog audio out at all, so this is required for sound |
| Small 4-8Ω speaker, 28-40mm | Whatever fits the print's speaker cavity |
| 5V micro-USB (or VSYS) power supply | |
| Hookup wire, heatshrink | |

## GPIO wiring (GP numbers)

The Pico W repurposes GP23, GP24, GP25, and GP29 internally for the CYW43
wireless chip -- they're not available on the header at all, unlike a plain
Pico. Everything below avoids them.

| Signal | GPIO | Physical pin |
|---|---|---|
| Candlestick 1 LED (+ via resistor) | GP2 | 4 |
| Candlestick 2 LED (+ via resistor) | GP3 | 5 |
| OLED SDA | GP4 | 6 |
| OLED SCL | GP5 | 7 |
| OLED VCC | 3V3 | 36 |
| OLED GND | GND | 8 (or any GND) |
| MAX98357A BCLK (SCK) | GP16 | 21 |
| MAX98357A LRC (WS) | GP17 | 22 |
| MAX98357A DIN (SD) | GP18 | 24 |
| MAX98357A VIN | VBUS (5V, only live over USB) | 40 |
| MAX98357A GND | GND | any |

Two hard constraints if you change any of these in `config.json`:

- **I2S**: the `ws` pin must always be `sck + 1` (a MicroPython/RP2040
  requirement, not a suggestion) -- so if you move `i2s_sck_pin` off GP16,
  `i2s_ws_pin` must move to match.
- **I2C**: GP4/GP5 are the Pico's default I2C0 pins, but any I2C-capable
  GPIO pair works if you update `i2c_scl_pin`/`i2c_sda_pin` together.

LED cathodes go to any GND pin through their resistor. All the pins above
are plain GPIO otherwise, so PWM (candles), I2C (display), and I2S (audio)
run independently with no shared hardware.

## Software setup

1. Flash MicroPython onto the Pico W: hold BOOTSEL, plug in USB, drag the
   latest **Raspberry Pi Pico W** `.uf2` from
   [micropython.org/download/RPI_PICO_W](https://micropython.org/download/RPI_PICO_W/)
   onto the drive that appears. Get a recent stable build -- this project
   uses `machine.I2S` (RP2 support landed a few releases back) and the
   modern `network.WLAN.IF_STA`/`IF_AP` API.
2. Copy everything under `pico-w/src/` onto the Pico's flash root, keeping
   the `lib/` subfolder as `lib/` (MicroPython puts `/lib` on `sys.path`
   automatically). Any tool works -- [Thonny](https://thonny.org/) is the
   easiest for a first pass, or `mpremote`:
   ```
   pip install mpremote
   mpremote connect auto cp -r pico-w/src/. :
   ```
3. Generate the sound cues on your PC (not the Pico -- see
   [../README.md](../README.md#sound-cues)) and copy the resulting
   `pico-w/sounds/*.wav` onto the Pico's flash under `/sounds/`.
4. Copy `pico-w/config.example.json` to the Pico as `/config.json` and edit
   if you want a different park, pins, or sound toggles.
5. Power-cycle the Pico. See [WIFI_SETUP.md](WIFI_SETUP.md) for connecting
   it to your network.

## Storage and memory notes

The Pico W has ~2MB of flash (minus whatever MicroPython's firmware uses)
and 264KB of RAM. The app and its vendored dependencies are small text
files, and the six sound cues at 22050Hz mono 16-bit come to well under
500KB total -- there's comfortable headroom, but this isn't a device to
pile large assets onto.

## Known limitations vs. the Pi Zero build

- **No hardware watchdog wired up.** The RP2040's watchdog timer caps out
  around 8.3 seconds, which is shorter than this app's 10-second HTTPS
  request timeout -- wiring one up as-is would risk resetting the device
  mid-request on an otherwise-fine slow response. `main.py` does catch
  unhandled exceptions and reset itself after a delay, which covers crashes
  but not true hangs.
- **No captive-portal network scan.** The setup page asks you to type your
  WiFi name rather than showing a dropdown of nearby networks (the Pi
  version scans and lists them). Simpler and more robust to run unattended.
- **Flicker/animation/sound aren't fully concurrent.** This is a single
  cooperative loop, not threads -- playing a sound or the change animation
  pauses candle flicker updates for a second or two rather than running
  alongside them. See the comment at the top of `main.py`.
