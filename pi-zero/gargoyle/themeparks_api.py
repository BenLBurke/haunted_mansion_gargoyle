"""Client for the community themeparks.wiki API (https://api.themeparks.wiki/v1/)."""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass

import requests

from gargoyle.parks import ParkInfo

log = logging.getLogger(__name__)

BASE_URL = "https://api.themeparks.wiki/v1"
REQUEST_TIMEOUT = 10


class ThemeParksApiError(RuntimeError):
    pass


@dataclass
class AttractionStatus:
    status: str  # OPERATING, DOWN, CLOSED, REFURBISHMENT
    wait_minutes: int | None
    last_updated: dt.datetime | None


@dataclass
class ParkHours:
    date: str
    opening_time: dt.datetime | None
    closing_time: dt.datetime | None


class ThemeParksClient:
    def __init__(self, park: ParkInfo, session: requests.Session | None = None):
        self.park = park
        self.session = session or requests.Session()

    def get_attraction_status(self) -> AttractionStatus:
        url = f"{BASE_URL}/entity/{self.park.attraction_entity_id}/live"
        data = self._get(url)
        live_data = data.get("liveData") or []
        if not live_data:
            raise ThemeParksApiError("No liveData in attraction response")
        entry = live_data[0]

        status = entry.get("status", "UNKNOWN")
        wait_minutes = None
        queue = entry.get("queue") or {}
        standby = queue.get("STANDBY") or {}
        if standby.get("waitTime") is not None:
            wait_minutes = int(standby["waitTime"])

        last_updated = _parse_iso(entry.get("lastUpdated"))
        return AttractionStatus(status=status, wait_minutes=wait_minutes, last_updated=last_updated)

    def get_todays_park_hours(self) -> ParkHours | None:
        url = f"{BASE_URL}/entity/{self.park.park_entity_id}/schedule"
        data = self._get(url)
        schedule = data.get("schedule") or []
        today = dt.datetime.now(dt.timezone.utc).astimezone(_zoneinfo(self.park.timezone)).date().isoformat()

        for entry in schedule:
            if entry.get("date") == today and entry.get("type") == "OPERATING":
                return ParkHours(
                    date=today,
                    opening_time=_parse_iso(entry.get("openingTime")),
                    closing_time=_parse_iso(entry.get("closingTime")),
                )
        return None

    def _get(self, url: str) -> dict:
        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            raise ThemeParksApiError(str(exc)) from exc


def _parse_iso(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def _zoneinfo(name: str):
    from zoneinfo import ZoneInfo

    return ZoneInfo(name)
