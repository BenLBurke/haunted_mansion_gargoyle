"""Thin wrapper around `nmcli` for WiFi connectivity checks and connection management.

Raspberry Pi OS (Bookworm and later) uses NetworkManager by default, so nmcli
is available out of the box -- no need to hand-roll wpa_supplicant/dhcpcd config.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import time

log = logging.getLogger(__name__)

NMCLI = "nmcli"
AP_CONNECTION_NAME = "GargoyleSetupAP"

_NMCLI_AVAILABLE = shutil.which(NMCLI) is not None
_warned_missing = False


def _warn_missing_once() -> None:
    # nmcli only exists on Linux/NetworkManager -- expected when developing
    # off-Pi (e.g. on Windows/macOS with --simulate). Not worth a traceback,
    # and definitely not worth repeating on every poll.
    global _warned_missing
    if not _warned_missing:
        log.info("nmcli not found; network checks are stubbed out (not running on a Pi?)")
        _warned_missing = True


def _run(args: list[str], timeout: int = 20) -> subprocess.CompletedProcess:
    return subprocess.run([NMCLI, *args], capture_output=True, text=True, timeout=timeout)


def is_connected() -> bool:
    if not _NMCLI_AVAILABLE:
        _warn_missing_once()
        return True
    try:
        result = _run(["-t", "-f", "CONNECTIVITY", "general"])
    except (subprocess.SubprocessError, FileNotFoundError):
        log.warning("nmcli call failed; assuming connected", exc_info=True)
        return True
    return result.stdout.strip() in ("full", "limited")


def has_saved_wifi_connection() -> bool:
    if not _NMCLI_AVAILABLE:
        _warn_missing_once()
        return True
    try:
        result = _run(["-t", "-f", "NAME,TYPE", "connection", "show"])
    except (subprocess.SubprocessError, FileNotFoundError):
        return True
    for line in result.stdout.splitlines():
        name, _, conn_type = line.partition(":")
        if conn_type == "802-11-wireless" and name != AP_CONNECTION_NAME:
            return True
    return False


def wait_for_connectivity(timeout_seconds: int, poll_interval: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if is_connected():
            return True
        time.sleep(poll_interval)
    return is_connected()


def scan_wifi_ssids() -> list[str]:
    if not _NMCLI_AVAILABLE:
        _warn_missing_once()
        return []
    try:
        result = _run(["-t", "-f", "SSID", "device", "wifi", "list", "--rescan", "yes"], timeout=30)
    except (subprocess.SubprocessError, FileNotFoundError):
        return []
    seen = []
    for line in result.stdout.splitlines():
        ssid = line.strip()
        if ssid and ssid not in seen:
            seen.append(ssid)
    return seen


def connect_to_wifi(ssid: str, password: str) -> tuple[bool, str]:
    if not _NMCLI_AVAILABLE:
        _warn_missing_once()
        return False, "nmcli not available on this system"
    try:
        result = _run(["device", "wifi", "connect", ssid, "password", password], timeout=45)
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        return False, str(exc)
    if result.returncode == 0:
        return True, "connected"
    return False, result.stderr.strip() or result.stdout.strip()


def reboot(delay_seconds: float = 4.0) -> None:
    import threading

    def _do_reboot():
        time.sleep(delay_seconds)
        try:
            subprocess.run(["systemctl", "reboot"], check=False)
        except (subprocess.SubprocessError, FileNotFoundError):
            log.warning("could not trigger reboot via systemctl", exc_info=True)

    threading.Thread(target=_do_reboot, daemon=True).start()
