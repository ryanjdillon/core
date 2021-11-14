import aiohttp
import pytest
from datetime import datetime
from typing import Callable, Union

from homeassistant.components.kartverket_tides.data import (
    parse_tide_data,
    KartverketTideData,
)
from homeassistant.components.kartverket_tides.api import KartverketTideApi
from tests.components.kartverket_tides.const import LATITUDE, LONGITUDE, LANG, INTERVAL


@pytest.fixture
def api_factory(aioclient_mock):
    """KartveketTideApi factory with defaults or passed kwargs"""

    def _api(**kwargs):
        api_kwargs = {
            "lat": LATITUDE,
            "lon": LONGITUDE,
            "lang": LANG,
            "interval": INTERVAL,
            "websession": aioclient_mock,
        }
        api_kwargs.update(**kwargs)
        return KartverketTideApi(**api_kwargs)

    return _api


@pytest.fixture
def api(api_factory):
    """KartverketApi with default test values"""
    return api_factory()


def test_parse_tide_data(tide_xml_etree: str):
    """
    Check that the tide data object is created and data is not empty
    """
    tides = parse_tide_data(tide_xml_etree)

    n_data_groups = len(tides.data)

    assert isinstance(tides, KartverketTideData)
    assert all(
        [
            tides.data[i].type
            in ["observation", "prediction", "weathereffect", "forecast"]
            for i in range(n_data_groups)
        ]
    )
    assert all([len(tides.data[i].waterlevels) > 0 for i in range(n_data_groups)])


# TODO mocking websession here
async def test_api_init(api_factory: Callable, aioclient_mock):
    """Test websession is created or reused"""
    api = api_factory(websession=aioclient_mock)
    assert isinstance(api.websession, aiohttp.ClientSession)


async def test_api_init_nosession(api_factory: Callable):
    """Test websession is created or reused"""
    api = api_factory(websession=None)
    assert isinstance(api.websession, aiohttp.ClientSession)


@pytest.mark.parametrize("tzone", [0, 1])
def test_api_fromtime(api: KartverketTideApi, tzone: int):
    """Test from time is created from beginning of current hour"""
    api.tzone = tzone
    assert api.fromtime.tzname == ("CET" | "CEST" if tzone else "UTC")


@pytest.mark.parametrize(
    "status,expected_tidetype", [(200, KartverketTideData), (500, None)]
)
async def test_api_updater(
    websession_factory: Callable,
    tide_xml_string: str,
    status: int,
    expected_tidetype: Union[KartverketTideApi, None],
):
    websession = websession_factory(status, tide_xml_string)
    api = api_factory(websession=websession)
    api.update()
    assert isinstance(api.tides, expected_tidetype)


def test_api_next_extreme(api):
    """Test valid next tidal time returned"""
    api.update()
    assert isinstance(api.next_time, datetime)


def test_api_current_waterlevel(api):
    assert isinstance(api.current_waterlevel, float)


def test_waterlevel_series(api):
    series = api.waterlevel_series

    # Check equal number of timestamps and waterlevels
    assert len(series["timestamp"]) == len(series["waterlevel"])

    # Check all values are of correct type
    for key, value_type in [("timestamp", datetime), ("waterlevel", float)]:
        assert all([isinstance(value, value_type) for value in series[key]])
