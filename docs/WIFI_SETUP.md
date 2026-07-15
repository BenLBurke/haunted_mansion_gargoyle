# WiFi setup (captive portal)

The gargoyle has no keyboard, screen-with-a-browser, or Ethernet port, so it
provisions WiFi the way most consumer IoT gadgets do: it becomes its own
WiFi hotspot until you hand it real credentials.

## How it decides to enter setup mode

On every boot, `gargoyle.wifi_setup.provision.needs_provisioning()` checks:

1. Does NetworkManager have any saved WiFi connection profile at all? If not
   (first boot, or after a factory reset), setup mode triggers immediately.
2. If it does have a saved network, the gargoyle tries to actually get
   online and waits up to `connectivity_timeout_seconds` (default 30s). If
   that fails -- e.g. you've moved it somewhere the old network doesn't
   reach -- it falls back to setup mode too.

This covers "first time I plug it in" and "I moved it and it can't find its
old WiFi" without any extra button or switch.

## Doing the setup

1. Power the gargoyle on (or power-cycle it if it's stuck offline).
2. On your phone or laptop, look for a WiFi network named **Gargoyle-Setup**
   (configurable via `ap_ssid` in `config.yaml`) and join it with the
   password **hauntedmansion** (`ap_password`).
3. Most phones will pop the setup page open automatically (that's what the
   `captive-portal-dnsmasq.conf` DNS redirect is for). If it doesn't, open a
   browser and go to `http://10.42.0.1/` or `http://gargoyle.local/`.
4. Pick your home WiFi network (or type the name manually if it's hidden),
   enter the password, choose which park's Haunted Mansion to track, and hit
   **Connect**.
5. The gargoyle reboots itself, joins your network, and starts polling wait
   times. The setup hotspot disappears once it's back up.

If the password was wrong or the network couldn't be reached, the portal
shows an error and lets you try again without rebooting.

## Troubleshooting

- **Nothing shows up when I look for "Gargoyle-Setup"**: check
  `journalctl -u gargoyle -f` for `nmcli hotspot` errors -- a common cause is
  a WiFi adapter that's rfkill-blocked (`rfkill list`, `rfkill unblock wifi`).
- **Portal loads but "Connect" fails**: double check the password, and that
  the network is 2.4GHz -- the Pi Zero 2 W's onboard radio doesn't do 5GHz.
- **It never leaves setup mode after connecting**: check
  `nmcli connection show` for a saved profile matching your SSID, and
  `journalctl -u gargoyle -f` around the time you hit Connect.
- **Reconfiguring a network it already knows**: reboot into range of the old
  network's failure condition doesn't apply once it's already connected. To
  force re-setup, delete the saved connection (`nmcli connection delete
  "<your ssid>"`) and reboot.
