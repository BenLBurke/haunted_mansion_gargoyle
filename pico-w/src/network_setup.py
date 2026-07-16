# WiFi connection management: joining a saved network, and starting the
# Pico's own AP for first-time (or moved-network) setup.
#
# Unlike the Pi's NetworkManager, MicroPython's `network` module doesn't
# remember WiFi credentials across reboots by itself -- we persist them
# ourselves in wifi_creds.json (separate from config.json, which is app
# settings, not secrets) and reconnect with them at boot.

import json
import time

import network

WIFI_CREDS_PATH = "wifi_creds.json"
AP_IP = "192.168.4.1"


def _sta_iface():
    try:
        return network.WLAN(network.WLAN.IF_STA)
    except AttributeError:
        return network.WLAN(network.STA_IF)


def _ap_iface():
    try:
        return network.WLAN(network.WLAN.IF_AP)
    except AttributeError:
        return network.WLAN(network.AP_IF)


def load_saved_wifi():
    try:
        with open(WIFI_CREDS_PATH) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    ssid = data.get("ssid")
    if not ssid:
        return None
    return ssid, data.get("password", "")


def save_wifi(ssid, password):
    with open(WIFI_CREDS_PATH, "w") as fh:
        json.dump({"ssid": ssid, "password": password}, fh)


def forget_wifi():
    try:
        import os

        os.remove(WIFI_CREDS_PATH)
    except OSError:
        pass


def connect_sta(ssid, password, timeout_seconds=30):
    sta = _sta_iface()
    sta.active(True)
    sta.connect(ssid, password)
    deadline = time.ticks_add(time.ticks_ms(), timeout_seconds * 1000)
    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        if sta.isconnected():
            return True
        time.sleep_ms(250)
    return sta.isconnected()


def is_connected():
    sta = _sta_iface()
    return sta.active() and sta.isconnected()


def start_ap(ssid, password):
    ap = _ap_iface()
    ap.active(False)
    time.sleep_ms(200)
    ap.active(True)

    try:
        ap.ifconfig((AP_IP, "255.255.255.0", AP_IP, AP_IP))
    except Exception:
        pass  # fall back to whatever address the driver picks by default

    try:
        ap.config(ssid=ssid, security=network.WLAN.SEC_WPA_WPA2, password=password)
    except (AttributeError, ValueError):
        # Older MicroPython: module-level constants instead of WLAN.SEC_*.
        ap.config(essid=ssid, password=password, authmode=network.AUTH_WPA_WPA2_PSK)

    return ap


def stop_ap():
    _ap_iface().active(False)
