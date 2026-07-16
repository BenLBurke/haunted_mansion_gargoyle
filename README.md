# haunted_mansion_gargoyle

A 3D-printed gargoyle holding two candlesticks that sits on your desk and
haunts you with live Haunted Mansion wait times from Disneyland or Walt
Disney World.

- Each candlestick has an LED that flickers like a real candle flame.
- A small screen embedded in the print shows the current wait time.
- A ghost/bat animation plays across the screen whenever the wait time changes.
- A speaker dings ominously when the wait goes down, and plays a cue when
  the park opens and closes for the day.
- No keyboard or monitor needed to set it up -- on first boot (or if it ever
  loses its WiFi) it broadcasts its own hotspot with a captive setup page so
  you can hand it your home WiFi from a phone.

There are two independent implementations, one per board -- pick whichever
you're building for:

| | [`pi-zero/`](pi-zero/) | [`pico-w/`](pico-w/) |
|---|---|---|
| Board | Raspberry Pi Zero 2 W (or Zero W) | Raspberry Pi Pico W (or Pico 2 W) |
| Runs | Linux + CPython | MicroPython, no OS |
| Cost/power | Higher | Lower, instant-on |
| Setup | SD card, `apt`/`pip`, systemd | Drag-and-drop firmware, copy files |

They share the same wait-time API ([themeparks.wiki](https://themeparks.wiki/))
and the same design (candle flicker, ghost/bat animation, WiFi captive
portal), but are separate codebases -- the Pico has no Linux underneath, so
none of the Pi build's libraries (Flask, Pillow, `requests`, systemd,
NetworkManager) apply there. See [pico-w/README.md](pico-w/README.md#why-this-is-a-separate-implementation-not-a-port)
for the full rundown of what's different and why.

Each has its own README, hardware/wiring docs, config, and test suite --
start there:

- [pi-zero/README.md](pi-zero/README.md)
- [pico-w/README.md](pico-w/README.md)

## Attribution

Wait times and schedule data come from the free, community-run
[themeparks.wiki](https://themeparks.wiki/) API. It's not affiliated with
Disney; be a good citizen and don't poll faster than each build's
`poll_interval_seconds` needs to be.
