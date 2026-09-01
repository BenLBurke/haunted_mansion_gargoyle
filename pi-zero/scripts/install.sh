#!/usr/bin/env bash
# Installs the gargoyle app on a Raspberry Pi OS (Bookworm+) Zero W / Zero 2 W.
# Run as: sudo bash scripts/install.sh
#
# /opt/gargoyle ends up as a real git clone of the canonical repo (not an
# rsync copy of whatever local checkout you ran this from) -- that's what
# lets OTA updates work afterwards: gargoyle-ota-check.service does a plain
# `git fetch`/`git checkout <tag>` against it. See docs/OTA.md.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run this with sudo: sudo bash scripts/install.sh" >&2
  exit 1
fi

INSTALL_DIR="/opt/gargoyle"
CONFIG_DIR="/etc/gargoyle"
REPO_URL="https://github.com/BenLBurke/haunted_mansion_gargoyle.git"
BOOT_CONFIG="/boot/firmware/config.txt"
[[ -f "$BOOT_CONFIG" ]] || BOOT_CONFIG="/boot/config.txt"

echo "==> Installing system packages"
apt-get update
apt-get install -y python3-venv python3-pip i2c-tools alsa-utils network-manager avahi-daemon git

echo "==> Setting hostname to gargoyle.local"
hostnamectl set-hostname gargoyle
sed -i "s/127.0.1.1.*/127.0.1.1\tgargoyle/" /etc/hosts || echo -e "127.0.1.1\tgargoyle" >> /etc/hosts

echo "==> Enabling I2C (for the OLED)"
raspi-config nonint do_i2c 0 || echo "raspi-config not available, enable I2C manually if needed"

echo "==> Enabling I2S DAC overlay (MAX98357A, for the speaker)"
if ! grep -q "^dtoverlay=max98357a" "$BOOT_CONFIG" 2>/dev/null; then
  echo "dtoverlay=max98357a" >> "$BOOT_CONFIG"
fi

echo "==> Deploying $INSTALL_DIR as a git clone of $REPO_URL"
if [[ -d "$INSTALL_DIR/.git" ]]; then
  git -C "$INSTALL_DIR" fetch origin
else
  rm -rf "$INSTALL_DIR"
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

echo "==> Checking out the latest release"
LATEST_TAG="$(python3 -c "
import json, urllib.request
req = urllib.request.Request(
    'https://api.github.com/repos/BenLBurke/haunted_mansion_gargoyle/releases/latest',
    headers={'User-Agent': 'gargoyle-install'},
)
with urllib.request.urlopen(req, timeout=15) as resp:
    print(json.load(resp)['tag_name'])
")"
git -C "$INSTALL_DIR" checkout "$LATEST_TAG"
echo "    checked out $LATEST_TAG"

echo "==> Creating virtualenv"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/pi-zero/requirements.txt"

echo "==> Generating sound cues"
(cd "$INSTALL_DIR/pi-zero" && "$INSTALL_DIR/venv/bin/python" -m gargoyle.audio.generate_tones)

echo "==> Writing default config"
mkdir -p "$CONFIG_DIR"
if [[ ! -f "$CONFIG_DIR/config.yaml" ]]; then
  cp "$INSTALL_DIR/pi-zero/config/config.example.yaml" "$CONFIG_DIR/config.yaml"
fi

echo "==> Installing captive-portal DNS redirect"
mkdir -p /etc/NetworkManager/dnsmasq-shared.d
cp "$INSTALL_DIR/pi-zero/systemd/captive-portal-dnsmasq.conf" /etc/NetworkManager/dnsmasq-shared.d/captive-portal.conf

echo "==> Installing systemd service"
cp "$INSTALL_DIR/pi-zero/systemd/gargoyle.service" /etc/systemd/system/gargoyle.service

read_config_value() {
  # Tiny scalar-only reader so this script doesn't need PyYAML -- $1 is the
  # config.yaml key, $2 is the fallback if it's missing or the file doesn't exist.
  python3 -c "
import re
try:
    with open('$CONFIG_DIR/config.yaml') as f:
        for line in f:
            m = re.match(r'$1:\s*([0-9.]+)', line.strip())
            if m:
                print(m.group(1))
                break
        else:
            print('$2')
except OSError:
    print('$2')
"
}

echo "==> Installing OTA update checker"
OTA_INTERVAL_HOURS="$(read_config_value ota_check_interval_hours 24)"
cp "$INSTALL_DIR/pi-zero/systemd/gargoyle-ota-check.service" /etc/systemd/system/gargoyle-ota-check.service
sed "s/OnUnitActiveSec=24h/OnUnitActiveSec=${OTA_INTERVAL_HOURS}h/" \
  "$INSTALL_DIR/pi-zero/systemd/gargoyle-ota-check.timer" > /etc/systemd/system/gargoyle-ota-check.timer

RESET_HOLD_SECONDS="$(read_config_value reset_hold_seconds 3)"

systemctl daemon-reload
systemctl enable gargoyle.service
systemctl restart gargoyle.service
systemctl enable --now gargoyle-ota-check.timer

cat <<EOF

==> Done! Installed release $LATEST_TAG.

If this is the first boot without WiFi configured, the gargoyle will start
broadcasting the "Gargoyle-Setup" WiFi network. Connect to it from your phone,
then open http://10.42.0.1/ (it should pop up automatically) to hand over
your home WiFi credentials.

Hold the reset button for ${RESET_HOLD_SECONDS} seconds any time to forget
WiFi and re-enter setup mode (also lets you pick a different park).

Edit /etc/gargoyle/config.yaml to change parks, GPIO pins, sound cues, etc.,
then \`sudo systemctl restart gargoyle\`.

OTA updates check for a newer GitHub release every ${OTA_INTERVAL_HOURS}h
(gargoyle-ota-check.timer) and roll back automatically if the service
doesn't come up healthy afterwards. See docs/OTA.md.

Logs: journalctl -u gargoyle -f
OTA update logs: journalctl -u gargoyle-ota-check -f
EOF
