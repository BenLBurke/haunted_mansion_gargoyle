"""Registry of supported resorts/parks and their Haunted Mansion attraction IDs.

IDs are from the community themeparks.wiki API (https://api.themeparks.wiki/v1/)
and were confirmed live against the API on 2026-07-15.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParkInfo:
    key: str
    label: str
    short_label: str  # fits on the OLED's header line
    park_entity_id: str
    attraction_entity_id: str
    timezone: str


PARKS: dict[str, ParkInfo] = {
    "disneyland": ParkInfo(
        key="disneyland",
        label="Disneyland Park (Anaheim)",
        short_label="Disneyland",
        park_entity_id="7340550b-c14d-4def-80bb-acdb51d49a66",
        attraction_entity_id="ff52cb64-c1d5-4feb-9d43-5dbd429bac81",
        timezone="America/Los_Angeles",
    ),
    "walt_disney_world": ParkInfo(
        key="walt_disney_world",
        label="Magic Kingdom (Walt Disney World)",
        short_label="Magic Kingdom",
        park_entity_id="75ea578a-adc8-4116-a54d-dccb60765ef9",
        attraction_entity_id="2551a77d-023f-4ab1-9a19-8afec0190f39",
        timezone="America/New_York",
    ),
}

DEFAULT_PARK_KEY = "disneyland"


def get_park(key: str) -> ParkInfo:
    try:
        return PARKS[key]
    except KeyError as exc:
        valid = ", ".join(PARKS)
        raise ValueError(f"Unknown park '{key}'. Valid options: {valid}") from exc
