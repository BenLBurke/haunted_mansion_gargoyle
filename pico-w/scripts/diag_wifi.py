# One-off connectivity diagnostic -- run directly on the device with:
#   mpremote connect <port> run pico-w/scripts/diag_wifi.py
#
# `mpremote run` takes over the device and executes this regardless of what
# main.py is currently doing, so it works even when you can't get an
# interactive REPL prompt (e.g. Ctrl+C not being forwarded by your terminal).
#
# Checks, in order: does the STA interface have a sane IP/gateway/DNS, can it
# resolve api.themeparks.wiki, and can it complete a raw TCP connection to it
# on port 443. Narrows a themeparks.wiki request timeout down to "WiFi/DNS
# problem" vs. "something blocking the outbound connection" vs. "the code
# itself" (if this script's TCP connect succeeds, the problem is upstream of
# here, most likely in the TLS handshake).

import network
import socket

sta = network.WLAN(network.WLAN.IF_STA)
print("ifconfig:", sta.ifconfig())

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
