# Decides whether the gargoyle needs first-time (or post-move) WiFi setup,
# and runs the captive portal flow if so.

import network_setup


def needs_provisioning(config):
    saved = network_setup.load_saved_wifi()
    if saved is None:
        return True
    ssid, password = saved
    ok = network_setup.connect_sta(ssid, password, timeout_seconds=config["connectivity_timeout_seconds"])
    return not ok


def run_provisioning(config):
    """Blocks, serving the setup portal, until WiFi credentials work. The
    device resets itself once that happens, so this never returns normally."""
    import wifi_portal

    network_setup.start_ap(config["ap_ssid"], config["ap_password"])
    wifi_portal.run(config)
