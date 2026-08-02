# Decides whether the gargoyle needs first-time (or post-move) WiFi setup,
# and runs the captive portal flow if so.
#
# `candles`, if given, is stepped continuously throughout -- both while
# trying saved credentials and while the captive portal is up -- so there's
# never a silent, dark stretch that's hard to tell apart from a hang.

import network_setup


def needs_provisioning(config, candles=None):
    def tick():
        if candles:
            for candle in candles:
                candle.step()

    saved = network_setup.load_saved_wifi()
    if saved is None:
        print("no saved WiFi credentials -- entering setup mode")
        return True

    ssid, password = saved
    print("found saved WiFi for '{}', attempting to connect...".format(ssid))
    ok = network_setup.connect_sta(
        ssid, password, timeout_seconds=config["connectivity_timeout_seconds"], on_tick=tick
    )
    if ok:
        print("connected to '{}'".format(ssid))
    else:
        print(
            "could not connect to '{}' within {}s -- entering setup mode".format(
                ssid, config["connectivity_timeout_seconds"]
            )
        )
    return not ok


def run_provisioning(config, candles=None):
    """Blocks, serving the setup portal, until WiFi credentials work. The
    device resets itself once that happens, so this never returns normally."""
    import wifi_portal

    network_setup.start_ap(config["ap_ssid"], config["ap_password"])
    wifi_portal.run(config, candles)
