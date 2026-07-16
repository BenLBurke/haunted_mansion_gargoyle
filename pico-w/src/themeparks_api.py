# Client for the community themeparks.wiki API (https://api.themeparks.wiki/v1/).
#
# Unlike the Pi version, this only ever makes ONE request per poll (the
# attraction's /live endpoint) rather than a separate /schedule call --
# /live already includes today's operatingHours, which saves a TLS
# handshake every cycle (worth it on a memory- and power-constrained board).
#
# Parsing is split from fetching (_parse_live_response takes an already
# decoded dict) so the parsing logic can be unit tested under CPython
# without a network stack at all.

from state import AttractionStatus, ParkHours, Snapshot

BASE_URL = "https://api.themeparks.wiki/v1"
REQUEST_TIMEOUT = 10


class ThemeParksApiError(Exception):
    pass


def format_local_time(iso_string):
    """"2026-07-15T09:00:00-04:00" -> "9:00am".

    No datetime/timezone module needed: themeparks.wiki already gives us the
    park's local wall-clock time with its UTC offset baked in (correct
    through DST changes), so we just slice the HH:MM straight out of the
    string instead of doing any timezone math.
    """
    hour = int(iso_string[11:13])
    minute = iso_string[14:16]
    suffix = "am" if hour < 12 else "pm"
    hour12 = hour % 12
    if hour12 == 0:
        hour12 = 12
    return "{}:{}{}".format(hour12, minute, suffix)


def parse_live_response(data):
    live_data = data.get("liveData") or []
    if not live_data:
        raise ThemeParksApiError("No liveData in response")
    entry = live_data[0]

    status = entry.get("status", "UNKNOWN")
    wait_minutes = None
    standby = (entry.get("queue") or {}).get("STANDBY") or {}
    if standby.get("waitTime") is not None:
        wait_minutes = int(standby["waitTime"])
    attraction = AttractionStatus(status=status, wait_minutes=wait_minutes)

    hours = None
    for block in entry.get("operatingHours") or []:
        if block.get("type") == "Operating":
            hours = ParkHours(
                opening_text=format_local_time(block["startTime"]),
                closing_text=format_local_time(block["endTime"]),
            )
            break

    return Snapshot(attraction=attraction, hours=hours)


def fetch_snapshot(park):
    import requests

    url = "{}/entity/{}/live".format(BASE_URL, park.attraction_entity_id)
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        try:
            if response.status_code != 200:
                raise ThemeParksApiError("HTTP {}".format(response.status_code))
            data = response.json()
        finally:
            response.close()
    except OSError as exc:
        # MicroPython doesn't support "raise X from Y" exception chaining.
        raise ThemeParksApiError(str(exc))

    return parse_live_response(data)
