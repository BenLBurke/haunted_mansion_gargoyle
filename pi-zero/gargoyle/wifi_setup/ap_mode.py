"""Starts/stops the Pi's own WiFi hotspot used for first-time setup, via NetworkManager."""

from __future__ import annotations

import logging
import subprocess

from gargoyle.network import AP_CONNECTION_NAME, NMCLI

log = logging.getLogger(__name__)


def start_ap(ssid: str, password: str, ifname: str = "wlan0") -> bool:
    try:
        subprocess.run([NMCLI, "connection", "delete", AP_CONNECTION_NAME], capture_output=True)
        result = subprocess.run(
            [
                NMCLI,
                "device",
                "wifi",
                "hotspot",
                "ifname",
                ifname,
                "con-name",
                AP_CONNECTION_NAME,
                "ssid",
                ssid,
                "password",
                password,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        log.error("failed to start AP mode", exc_info=True)
        return False

    if result.returncode != 0:
        log.error("nmcli hotspot failed: %s", result.stderr.strip())
        return False
    log.info("AP mode started: ssid=%s", ssid)
    return True


def stop_ap() -> None:
    try:
        subprocess.run([NMCLI, "connection", "down", AP_CONNECTION_NAME], capture_output=True, timeout=15)
    except (subprocess.SubprocessError, FileNotFoundError):
        log.debug("failed to stop AP mode (may not have been running)", exc_info=True)
