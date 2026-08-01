# WiFi setup (captive portal)

Same idea as the Pi Zero build, implemented from scratch on top of
MicroPython's `network` module instead of NetworkManager, since the Pico has
no OS-level network manager to lean on.

## How it decides to enter setup mode

On every boot, `provision.needs_provisioning()` checks:

1. Do we have WiFi credentials saved in `/wifi_creds.json` at all? If not
   (first boot, or after a factory reset), setup mode triggers immediately.
2. If we do, it tries to actually join that network and waits up to
   `connectivity_timeout_seconds` (default 30s). If that fails -- e.g.
   you've moved it somewhere the old network doesn't reach -- it falls back
   to setup mode too.

## Doing the setup

1. Power the gargoyle on (or power-cycle it if it's stuck offline).
2. On your phone or laptop, look for a WiFi network named **Gargoyle-Setup**
   (configurable via `ap_ssid` in `config.json`) and join it with the
   password **hauntedmansion** (`ap_password`).
3. Most phones will pop the setup page open automatically -- the Pico runs
   its own tiny DNS server while in setup mode that answers every lookup
   with its own address, which is what triggers that. If it doesn't open on
   its own, browse to `http://192.168.4.1/`.
4. Type your home WiFi's name and password (there's no network scan/dropdown
   on this version -- see docs/HARDWARE.md for why), choose which park's
   Haunted Mansion to track, and hit **Connect**.
5. The gargoyle reboots itself, joins your network, and starts polling wait
   times. The setup hotspot disappears once it's back up.

If the password was wrong or the network couldn't be reached, the portal
shows an error and lets you try again without rebooting.

## Troubleshooting

- **Nothing shows up when I look for "Gargoyle-Setup"**: connect a serial
  console (`mpremote connect auto` or Thonny's Shell) and check the printed
  output for AP-related errors.
- **Portal loads but "Connect" fails**: double check the password, and that
  the network is 2.4GHz -- the Pico W's onboard radio doesn't do 5GHz.
- **It never leaves setup mode after connecting**: watch the serial console
  during the connect attempt; `network_setup.connect_sta()` prints nothing
  itself, but an uncaught exception in the portal handler will.
- **Reconfiguring a network it already knows**: delete `/wifi_creds.json`
  from the Pico's flash (via Thonny/`mpremote`) and power-cycle to force
  re-setup.
