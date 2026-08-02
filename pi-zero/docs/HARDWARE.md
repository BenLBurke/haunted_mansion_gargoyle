# Hardware

## Bill of materials

| Part | Notes |
|---|---|
| Raspberry Pi Zero 2 W | Needs onboard WiFi -- a plain Pi Zero (no "W") won't work. Zero W also fine, just slower. |
| MicroSD card, 8GB+ | Raspberry Pi OS Lite (Bookworm or later, 32- or 64-bit) |
| SSD1306 OLED, 128x64, I2C | 0.91" or 0.96", cheap and common. This is the "small screen" embedded in the print. |
| 2x 5mm LEDs, warm/amber or "flicker flame" tint | One per candlestick |
| 2x 220-330Ω resistors | Current limiting for the LEDs |
| MAX98357A I2S 3W Class-D amp breakout | The Pi Zero has no analog audio jack, so the speaker needs an I2S DAC/amp like this one |
| Small 4-8Ω speaker, 28-40mm | Whatever fits the print's speaker cavity |
| 5V/2.5A micro-USB power supply | Amp + speaker + display draw more than a bare Pi |
| Hookup wire, heatshrink | |

## GPIO wiring (BCM numbering)

| Signal | GPIO (BCM) | Physical pin |
|---|---|---|
| Candlestick 1 LED (+ via resistor) | GPIO17 | 11 |
| Candlestick 2 LED (+ via resistor) | GPIO27 | 13 |
| OLED SDA | GPIO2 | 3 |
| OLED SCL | GPIO3 | 5 |
| OLED VCC | 3.3V | 1 |
| OLED GND | GND | 9 |
| MAX98357A BCLK | GPIO18 | 12 |
| MAX98357A LRC (WSEL) | GPIO19 | 35 |
| MAX98357A DIN | GPIO21 | 40 |
| MAX98357A VIN | 5V | 2 |
| MAX98357A GND | GND | 6 |
| Reset button (other leg to GND) | GPIO22 | 15 |

The reset button just needs a momentary push button between GPIO22 and any
GND pin -- `gpiozero.Button` uses the internal pull-up, so no external
resistor is needed. Hold it for `reset_hold_seconds` (default 3s) to forget
WiFi and reboot into setup mode; worth routing to a small hole in the print
or a discreet spot on the base so it's reachable without opening it up.

LED cathodes go to any GND pin through their resistor. GPIO pins and the I2S
pins are fixed by the `max98357a` device tree overlay (set up automatically
by `scripts/install.sh`) -- don't move BCLK/LRC/DIN elsewhere without also
changing the overlay. The candlestick LED pins are configurable in
`config.yaml` if you need to route around a pin that's already spoken for.

Double-check your MAX98357A breakout's GAIN/SD pins against its datasheet --
most boards default to a sensible gain with GAIN floating and are enabled
with SD floating or pulled high; only wire them if you want a specific fixed
gain.

## 3D print integration notes

A few things that make wiring painless once everything's inside the print:

- **OLED window**: a rectangular cutout sized to the glass, not the whole
  PCB, with standoff posts behind it for the four corner mounting holes.
  Leave a lip so the screen doesn't fall through when the bezel is glued/screwed on.
- **Candlestick flames**: hollow the candlestick tips and either use a
  frosted/translucent filament (light-diffusing PLA or a resin swap at the
  tip) or drill and sand the tip to frost it, so the LED underneath reads as
  a soft glow rather than a single hard point of light.
- **Speaker grille**: a small cluster of ~1.5mm holes over the speaker
  cavity (e.g. in the gargoyle's open mouth) gets sound out without a
  visible gap. Keep some free air volume behind the speaker cone -- don't
  wedge it directly against a wall.
- **Cable routing**: run a channel from the Pi's cavity out to each
  candlestick and to the OLED window so wires aren't pinched when the print
  halves come together. Leave the Pi's USB power port and the SD card
  reachable from a removable base or back panel -- you'll want SD access for
  re-flashing and the power port for, well, power.
- **Ventilation**: a few small vents near the Pi keep the amp and Pi from
  running warm inside an enclosed resin/PLA shell.

## Software setup

1. Flash Raspberry Pi OS Lite to the SD card (Raspberry Pi Imager lets you
   pre-configure a hostname/SSH key, but you do *not* need to pre-configure
   WiFi -- that's what the captive portal is for).
2. Boot it, SSH in (or use a keyboard/monitor once), and run the installer.
   It clones the repo itself (into `/opt/gargoyle`, pinned to the latest
   tagged release), so you don't need to `git clone` it yourself first:
   ```
   curl -fsSL https://raw.githubusercontent.com/BenLBurke/haunted_mansion_gargoyle/main/pi-zero/scripts/install.sh | sudo bash
   ```
   (or clone the repo and run `sudo bash pi-zero/scripts/install.sh` from
   within it -- same result either way.)
3. See [WIFI_SETUP.md](WIFI_SETUP.md) for connecting it to your network,
   and [OTA.md](OTA.md) for how it keeps itself updated afterwards.
