import pytest

from parks import PARKS, get_park


def test_get_park_returns_registry_entry():
    park = get_park("disneyland")
    assert park.label == "Disneyland Park (Anaheim)"
    assert park.attraction_entity_id == "ff52cb64-c1d5-4feb-9d43-5dbd429bac81"


def test_get_park_raises_on_unknown_key():
    with pytest.raises(ValueError):
        get_park("magic_kingdom_but_typo")


def test_all_parks_have_distinct_entity_ids():
    attraction_ids = [p.attraction_entity_id for p in PARKS.values()]
    assert len(attraction_ids) == len(set(attraction_ids))
