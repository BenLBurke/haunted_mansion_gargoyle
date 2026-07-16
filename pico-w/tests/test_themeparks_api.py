import pytest

from themeparks_api import ThemeParksApiError, format_local_time, parse_live_response


@pytest.mark.parametrize(
    "iso, expected",
    [
        ("2026-07-15T09:00:00-04:00", "9:00am"),
        ("2026-07-15T00:00:00-04:00", "12:00am"),
        ("2026-07-15T12:00:00-04:00", "12:00pm"),
        ("2026-07-15T23:30:00-04:00", "11:30pm"),
        ("2026-07-15T08:30:00+02:00", "8:30am"),
    ],
)
def test_format_local_time(iso, expected):
    assert format_local_time(iso) == expected


def test_parse_live_response_operating_with_wait():
    data = {
        "liveData": [
            {
                "status": "OPERATING",
                "queue": {"STANDBY": {"waitTime": 35}},
                "operatingHours": [
                    {"type": "Operating", "startTime": "2026-07-15T09:00:00-04:00", "endTime": "2026-07-15T23:00:00-04:00"},
                    {"type": "Extended Evening", "startTime": "2026-07-15T23:00:00-04:00", "endTime": "2026-07-16T01:00:00-04:00"},
                ],
            }
        ]
    }

    snapshot = parse_live_response(data)

    assert snapshot.attraction.status == "OPERATING"
    assert snapshot.attraction.wait_minutes == 35
    assert snapshot.hours.opening_text == "9:00am"
    assert snapshot.hours.closing_text == "11:00pm"


def test_parse_live_response_closed_has_no_wait_time():
    data = {"liveData": [{"status": "CLOSED", "queue": {"STANDBY": {"waitTime": None}}, "operatingHours": []}]}

    snapshot = parse_live_response(data)

    assert snapshot.attraction.status == "CLOSED"
    assert snapshot.attraction.wait_minutes is None
    assert snapshot.hours is None


def test_parse_live_response_raises_on_empty_live_data():
    with pytest.raises(ThemeParksApiError):
        parse_live_response({"liveData": []})
