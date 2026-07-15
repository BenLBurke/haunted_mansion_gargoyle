"""Captive-portal web app for first-time (or post-move) WiFi setup.

While the gargoyle can't reach a known network, it broadcasts its own AP
(see ap_mode.py) and serves this tiny Flask app so you can point a phone at
it and hand over your home WiFi credentials -- no keyboard/monitor needed.
"""

from __future__ import annotations

import logging

from flask import Flask, redirect, render_template, request

from gargoyle import network
from gargoyle.parks import PARKS

log = logging.getLogger(__name__)

# URLs various OSes probe to detect (and auto-open) a captive portal.
CAPTIVE_PROBE_PATHS = [
    "/generate_204",
    "/gen_204",
    "/hotspot-detect.html",
    "/library/test/success.html",
    "/ncsi.txt",
    "/connecttest.txt",
    "/canonical.html",
    "/success.txt",
]


def create_app(on_connected) -> Flask:
    """`on_connected(ssid, park_key)` is called once nmcli reports a successful join."""
    app = Flask(__name__)

    @app.get("/")
    def index():
        ssids = network.scan_wifi_ssids()
        parks = [(info.key, info.label) for info in PARKS.values()]
        return render_template("index.html", ssids=ssids, parks=parks, error=None)

    @app.post("/connect")
    def connect():
        ssid = request.form.get("ssid") or request.form.get("ssid_manual", "")
        password = request.form.get("password", "")
        park_key = request.form.get("park")

        if not ssid:
            ssids = network.scan_wifi_ssids()
            parks = [(info.key, info.label) for info in PARKS.values()]
            return render_template("index.html", ssids=ssids, parks=parks, error="Please choose or enter a network name.")

        ok, detail = network.connect_to_wifi(ssid, password)
        if not ok:
            ssids = network.scan_wifi_ssids()
            parks = [(info.key, info.label) for info in PARKS.values()]
            return render_template(
                "index.html", ssids=ssids, parks=parks, error=f"Couldn't join '{ssid}': {detail}"
            )

        on_connected(ssid, park_key)
        return render_template("success.html", ssid=ssid)

    @app.route("/<path:_path>")
    def catch_all(_path):
        return redirect("/")

    for probe_path in CAPTIVE_PROBE_PATHS:
        app.add_url_rule(probe_path, f"probe_{probe_path}", lambda: redirect("/"))

    return app
