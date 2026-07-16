import datetime as dt
from unittest.mock import MagicMock

import pytest

from gargoyle.parks import PARKS
from gargoyle.themeparks_api import ThemeParksApiError, ThemeParksClient


def _response(json_body, status_ok=True):
    resp = MagicMock()
    resp.json.return_value = json_body
    if not status_ok:
        resp.raise_for_status.side_effect = Exception("boom")
    return resp


def test_get_attraction_status_operating():
    session = MagicMock()
    session.get.return_value = _response(
        {
            "liveData": [
                {
                    "status": "OPERATING",
                    "queue": {"STANDBY": {"waitTime": 35}},
                    "lastUpdated": "2026-07-15T03:22:29.475Z",
                }
            ]
        }
    )
    client = ThemeParksClient(PARKS["disneyland"], session=session)

    status = client.get_attraction_status()

    assert status.status == "OPERATING"
    assert status.wait_minutes == 35
    assert status.last_updated == dt.datetime(2026, 7, 15, 3, 22, 29, 475000, tzinfo=dt.timezone.utc)


def test_get_attraction_status_closed_has_no_wait_time():
    session = MagicMock()
    session.get.return_value = _response(
        {"liveData": [{"status": "CLOSED", "queue": {"STANDBY": {"waitTime": None}}, "lastUpdated": None}]}
    )
    client = ThemeParksClient(PARKS["walt_disney_world"], session=session)

    status = client.get_attraction_status()

    assert status.status == "CLOSED"
    assert status.wait_minutes is None


def test_get_attraction_status_raises_on_empty_live_data():
    session = MagicMock()
    session.get.return_value = _response({"liveData": []})
    client = ThemeParksClient(PARKS["disneyland"], session=session)

    with pytest.raises(ThemeParksApiError):
        client.get_attraction_status()


def test_get_attraction_status_wraps_request_errors():
    import requests

    session = MagicMock()
    session.get.side_effect = requests.ConnectionError("no network")
    client = ThemeParksClient(PARKS["disneyland"], session=session)

    with pytest.raises(ThemeParksApiError):
        client.get_attraction_status()
