"""Ties together AP mode + the captive portal into the first-time WiFi setup flow."""

from __future__ import annotations

import logging

from gargoyle import network
from gargoyle.config import Config
from gargoyle.wifi_setup import ap_mode
from gargoyle.wifi_setup.portal import create_app

log = logging.getLogger(__name__)


def needs_provisioning(config: Config) -> bool:
    if not network.has_saved_wifi_connection():
        return True
    return not network.wait_for_connectivity(config.connectivity_timeout_seconds)


def run_provisioning(config: Config) -> None:
    """Blocks, serving the captive portal, until the user submits working WiFi credentials.

    On success the device reboots itself so it comes back up already joined
    to the new network with the AP torn down cleanly.
    """
    if not ap_mode.start_ap(config.ap_ssid, config.ap_password):
        log.error("could not start setup AP; will retry connectivity check instead of provisioning")
        return

    def on_connected(ssid: str, park_key: str | None) -> None:
        log.info("WiFi connected to '%s' during provisioning", ssid)
        if park_key:
            config.park = park_key
            config.save()
        network.reboot()

    app = create_app(on_connected)
    log.info(
        "Provisioning portal live. Connect to WiFi '%s' and browse to http://10.42.0.1/", config.ap_ssid
    )
    app.run(host="0.0.0.0", port=config.portal_port)
