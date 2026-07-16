#!/usr/bin/env bash
# Installs the gargoyle app on a Raspberry Pi OS (Bookworm+) Zero W / Zero 2 W.
# Run from a clone of this repo: sudo bash scripts/install.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run this with sudo: sudo bash scripts/install.sh" >&2
  exit 1
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="/opt/gargoyle"
CONFIG_DIR="/etc/gargoyle"
BOOT_CONFIG="/boot/firmware/config.txt"
[[ -f "$BOOT_CONFIG" ]] || BOOT_CONFIG="/boot/config.txt"

echo "==> Installing system packages"
apt-get update
apt-get install -y python3-venv python3-pip i2c-tools alsa-utils network-manager avahi-daemon rsync

echo "==> Setting hostname to gargoyle.local"
hostnamectl set-hostname gargoyle
sed -i "s/127.0.1.1.*/127.0.1.1\tgargoyle/" /etc/hosts || echo -e "127.0.1.1\tgargoyle" >> /etc/hosts

echo "==> Enabling I2C (for the OLED)"
raspi-config nonint do_i2c 0 || echo "raspi-config not available, enable I2C manually if needed"

echo "==> Enabling I2S DAC overlay (MAX98357A, for the speaker)"
if ! grep -q "^dtoverlay=max98357a" "$BOOT_CONFIG" 2>/dev/null; then
  echo "dtoverlay=max98357a" >> "$BOOT_CONFIG"
fi

echo "==> Copying app to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
rsync -a --delete --exclude venv --exclude __pycache__ --exclude '.git' "$REPO_DIR"/ "$INSTALL_DIR"/

echo "==> Creating virtualenv"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

echo "==> Generating sound cues"
"$INSTALL_DIR/venv/bin/python" -m gargoyle.audio.generate_tones

echo "==> Writing default config"
mkdir -p "$CONFIG_DIR"
if [[ ! -f "$CONFIG_DIR/config.yaml" ]]; then
  cp "$INSTALL_DIR/config/config.example.yaml" "$CONFIG_DIR/config.yaml"
fi

echo "==> Installing captive-portal DNS redirect"
mkdir -p /etc/NetworkManager/dnsmasq-shared.d
cp "$INSTALL_DIR/systemd/captive-portal-dnsmasq.conf" /etc/NetworkManager/dnsmasq-shared.d/captive-portal.conf

echo "==> Installing systemd service"
cp "$INSTALL_DIR/systemd/gargoyle.service" /etc/systemd/system/gargoyle.service
systemctl daemon-reload
systemctl enable gargoyle.service
systemctl restart gargoyle.service

cat <<'EOF'

==> Done!

If this is the first boot without WiFi configured, the gargoyle will start
broadcasting the "Gargoyle-Setup" WiFi network. Connect to it from your phone,
then open http://10.42.0.1/ (it should pop up automatically) to hand over
your home WiFi credentials.

Edit /etc/gargoyle/config.yaml to change parks, GPIO pins, sound cues, etc.,
then `sudo systemctl restart gargoyle`.

Logs: journalctl -u gargoyle -f
EOF
