# Registry of supported resorts/parks and their Haunted Mansion attraction IDs.
#
# IDs are from the community themeparks.wiki API (https://api.themeparks.wiki/v1/)
# and were confirmed live against the API on 2026-07-15. Kept in sync by hand
# with pi-zero/gargoyle/parks.py -- if you add a park there, add it here too.
#
# Plain classes rather than dataclasses: MicroPython doesn't ship the
# dataclasses module, and this needs to run unmodified on both the Pico and
# under CPython (for tests).
#
# No timezone field here, unlike the Pi version: themeparks.wiki returns
# schedule timestamps with the park's local UTC offset already embedded
# (e.g. "2026-07-15T08:30:00-04:00"), which is correct through DST changes
# automatically. The Pico has no tzdata to do that math itself, so
# themeparks_api.py just reads the offset straight off each timestamp
# instead of needing one.


class ParkInfo:
    def __init__(self, key, label, short_label, park_entity_id, attraction_entity_id):
        self.key = key
        self.label = label
        self.short_label = short_label
        self.park_entity_id = park_entity_id
        self.attraction_entity_id = attraction_entity_id


PARKS = {
    "disneyland": ParkInfo(
        key="disneyland",
        label="Disneyland Park (Anaheim)",
        short_label="Disneyland",
        park_entity_id="7340550b-c14d-4def-80bb-acdb51d49a66",
        attraction_entity_id="ff52cb64-c1d5-4feb-9d43-5dbd429bac81",
    ),
    "walt_disney_world": ParkInfo(
        key="walt_disney_world",
        label="Magic Kingdom (Walt Disney World)",
        short_label="Magic Kingdom",
        park_entity_id="75ea578a-adc8-4116-a54d-dccb60765ef9",
        attraction_entity_id="2551a77d-023f-4ab1-9a19-8afec0190f39",
    ),
}

DEFAULT_PARK_KEY = "disneyland"


def get_park(key):
    park = PARKS.get(key)
    if park is None:
        raise ValueError("Unknown park '{}'. Valid options: {}".format(key, ", ".join(PARKS)))
    return park
