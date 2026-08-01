# One-off connectivity diagnostic -- run directly on the device with:
#   mpremote connect <port> run pico-w/scripts/diag_wifi.py
#
# `mpremote run` takes over the device and executes this regardless of what
# main.py is currently doing, so it works even when you can't get an
# interactive REPL prompt (e.g. Ctrl+C not being forwarded by your terminal).
#
# Checks: does the STA interface have a sane IP/gateway/DNS, can it resolve
# api.themeparks.wiki, and can it complete a raw TCP connection to it on
# port 443. If the IP looks bad (0.0.0.0 -- isconnected() can report True
# before DHCP actually finishes), it forces a disconnect/reconnect using the
# saved credentials and re-checks, so a "just needed to rejoin" fix gets
# confirmed in the same run instead of needing another round trip.

import json
import time

import network
import socket

sta = network.WLAN(network.WLAN.IF_STA)


def report():
    cfg = sta.ifconfig()
    print("isconnected:", sta.isconnected(), " ifconfig:", cfg)
    return cfg[0] != "0.0.0.0"


print("--- current state ---")
ok = report()

if not ok:
    print("--- IP looks bad, forcing a reconnect ---")
    try:
        with open("wifi_creds.json") as fh:
            creds = json.load(fh)
        ssid, password = creds["ssid"], creds.get("password", "")
    except (OSError, KeyError, ValueError) as exc:
        print("couldn't read saved credentials:", exc)
        ssid = None

    if ssid:
        sta.disconnect()
        time.sleep_ms(500)
        sta.connect(ssid, password)
        deadline = time.ticks_add(time.ticks_ms(), 20000)
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            if sta.isconnected() and sta.ifconfig()[0] != "0.0.0.0":
                break
            time.sleep_ms(250)
        print("--- state after reconnect ---")
        ok = report()

if ok:
    print("resolving api.themeparks.wiki...")
    try:
        info = socket.getaddrinfo("api.themeparks.wiki", 443)
        print("resolved:", info)
    except Exception as e:
        print("DNS FAILED:", e)
        info = None

    if info:
        addr = info[0][-1]
        s = socket.socket()
        s.settimeout(15)
        print("connecting to", addr, "...")
        try:
            s.connect(addr)
            print("TCP CONNECT OK")
            s.close()
        except Exception as e:
            print("TCP CONNECT FAILED:", e)
else:
    print("still no valid IP after reconnect attempt -- likely a router/DHCP issue, not the app")
