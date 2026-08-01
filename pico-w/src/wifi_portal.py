# Captive-portal web app for first-time (or post-move) WiFi setup: a tiny
# DNS server that answers every query with the Pico's own address (so phones
# auto-pop the setup page) plus a tiny HTTP server for the setup form.
#
# DNS spoofing technique adapted from the well-known
# p-doyle/Micropython-DNSServer-Captive-Portal pattern.

import gc
import socket

import asyncio

from gargoyle_config import save as save_config
from network_setup import AP_IP, connect_sta, save_wifi
from parks import PARKS

PORTAL_PORT = 80

PAGE_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gargoyle Setup</title>
<style>
body {{ font-family: sans-serif; background: #14121a; color: #e8e2f0; margin: 0; padding: 24px 16px; }}
.card {{ max-width: 380px; margin: 0 auto; }}
label {{ display: block; margin: 16px 0 6px; font-size: 0.9rem; color: #c9bfdb; }}
input, select {{ width: 100%; box-sizing: border-box; padding: 10px; border-radius: 8px; border: 1px solid #4a4160; background: #1f1c29; color: #e8e2f0; font-size: 1rem; }}
button {{ width: 100%; margin-top: 22px; padding: 12px; border-radius: 8px; border: none; background: #6a3fb5; color: white; font-size: 1.05rem; font-weight: 600; }}
.error {{ background: #4a1f2b; border: 1px solid #8a3049; color: #ffc2d1; padding: 10px 12px; border-radius: 8px; margin-top: 16px; }}
</style></head>
<body><div class="card">
<div style="font-size:2rem">&#128123;</div>
<h1>Welcome to the Gargoyle</h1>
<p>Connect it to your WiFi so it can watch the Haunted Mansion wait times.</p>
{error}
<form method="post" action="/connect">
<label for="ssid">WiFi network name (SSID)</label>
<input type="text" id="ssid" name="ssid" autocapitalize="off" autocorrect="off">
<label for="password">Password</label>
<input type="password" id="password" name="password">
<label for="park">Which park?</label>
<select id="park" name="park">
{park_options}
</select>
<button type="submit">Connect</button>
</form>
</div></body></html>
"""

SUCCESS_PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gargoyle Setup</title>
<style>body {{ font-family: sans-serif; background: #14121a; color: #e8e2f0; text-align: center; padding: 60px 16px; }}</style>
</head><body>
<div style="font-size:2.2rem">&#129415;</div>
<h1>Joining {ssid}...</h1>
<p>The gargoyle is restarting and will come to life shortly. You can close this page.</p>
</body></html>
"""


def _park_options():
    return "\n".join('<option value="{}">{}</option>'.format(key, info.label) for key, info in PARKS.items())


def _render_index(error=""):
    error_html = '<div class="error">{}</div>'.format(error) if error else ""
    return PAGE_TEMPLATE.format(error=error_html, park_options=_park_options())


def _url_decode(s):
    s = s.replace("+", " ")
    out = ""
    i = 0
    while i < len(s):
        if s[i] == "%" and i + 2 < len(s):
            try:
                out += chr(int(s[i + 1 : i + 3], 16))
                i += 3
                continue
            except ValueError:
                pass
        out += s[i]
        i += 1
    return out


def _parse_form(body):
    fields = {}
    for pair in body.split("&"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            fields[_url_decode(k)] = _url_decode(v)
    return fields


class DNSQuery:
    def __init__(self, data):
        self.data = data
        self.domain = ""
        if (data[2] >> 3) & 15 == 0:  # standard query opcode
            i = 12
            length = data[i]
            while length != 0:
                self.domain += data[i + 1 : i + 1 + length].decode("utf-8") + "."
                i += length + 1
                length = data[i]

    def response(self, ip):
        packet = self.data[:2] + b"\x81\x80"
        packet += self.data[4:6] * 2 + b"\x00\x00\x00\x00"
        packet += self.data[12:]
        packet += b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04"
        packet += bytes([int(x) for x in ip.split(".")])
        return packet


async def _run_dns_server(ip):
    udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udps.setblocking(False)
    udps.bind(("0.0.0.0", 53))
    try:
        while True:
            try:
                data, addr = udps.recvfrom(512)
            except OSError:
                await asyncio.sleep_ms(50)
                continue
            try:
                query = DNSQuery(data)
                if query.domain:
                    udps.sendto(query.response(ip), addr)
            except Exception as exc:
                print("dns query error:", exc)
            gc.collect()
    finally:
        udps.close()


async def _write_response(writer, status, body, content_type="text/html"):
    body_bytes = body.encode()
    header = "HTTP/1.0 {} OK\r\nContent-Type: {}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n".format(
        status, content_type, len(body_bytes)
    )
    writer.write(header.encode())
    writer.write(body_bytes)
    await writer.drain()


async def _write_redirect(writer, location):
    header = "HTTP/1.0 302 Found\r\nLocation: http://{}{}\r\nConnection: close\r\n\r\n".format(AP_IP, location)
    writer.write(header.encode())
    await writer.drain()


async def _handle_connect(writer, body, ctx):
    fields = _parse_form(body)
    ssid = fields.get("ssid", "").strip()
    password = fields.get("password", "")
    park = fields.get("park", "")

    if not ssid:
        await _write_response(writer, 200, _render_index("Please enter a network name."))
        return

    ok = connect_sta(ssid, password, timeout_seconds=20)
    if not ok:
        await _write_response(writer, 200, _render_index("Couldn't join '{}'. Check the password and try again.".format(ssid)))
        return

    save_wifi(ssid, password)
    if park in PARKS:
        ctx["config"]["park"] = park
        save_config(ctx["config"])

    await _write_response(writer, 200, SUCCESS_PAGE.format(ssid=ssid))
    ctx["connected"] = True


async def _handle_client(reader, writer, ctx):
    try:
        request_line = await reader.readline()
        if not request_line:
            return
        parts = request_line.decode().split()
        if len(parts) < 2:
            return
        method, path = parts[0], parts[1]

        headers = {}
        while True:
            line = await reader.readline()
            if not line or line == b"\r\n":
                break
            if b":" in line:
                k, v = line.decode().split(":", 1)
                headers[k.strip().lower()] = v.strip()

        content_length = int(headers.get("content-length", 0))
        body = await reader.readexactly(content_length) if content_length else b""

        if method == "POST" and path == "/connect":
            await _handle_connect(writer, body.decode(), ctx)
        elif method == "GET" and path == "/":
            await _write_response(writer, 200, _render_index())
        else:
            # Captive-portal probe URLs (Android/iOS/Windows) and anything
            # else all land here, and get redirected to the setup page.
            await _write_redirect(writer, "/")
    except Exception as exc:
        print("portal client error:", exc)
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        gc.collect()


async def _serve(config, ctx):
    asyncio.create_task(_run_dns_server(AP_IP))
    asyncio.create_task(asyncio.start_server(lambda r, w: _handle_client(r, w, ctx), "0.0.0.0", PORTAL_PORT))

    while not ctx["connected"]:
        await asyncio.sleep_ms(500)
    await asyncio.sleep_ms(1500)  # let the success response reach the browser


def run(config):
    """Blocks, serving the captive portal, until WiFi credentials work. Resets the device on success."""
    ctx = {"config": config, "connected": False}
    asyncio.run(_serve(config, ctx))

    import machine

    machine.reset()
