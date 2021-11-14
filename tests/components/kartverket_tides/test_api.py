import pytest
from datetime import datetime
from typing import Callable, Union


from homeassistant.components.kartverket_tides.data import (
    parse_tide_data,
    KartverketTideData,
)
from homeassistant.components.kartverket_tides.api import KartverketTideApi


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


async def test_api_init(api_factory: Callable, mock_asyncio_run):
    """Test websession is created or reused"""
    api = api_factory(websession=None)
    assert api.websession is not None
    assert mock_asyncio_run.called


@pytest.mark.parametrize(
    "status,expected_tidetype", [(200, KartverketTideData), (500, type(None))]
)
async def test_api_updater(
    api_factory: Callable,
    websession_factory: Callable,
    tide_xml_str: str,
    status: int,
    expected_tidetype: Union[KartverketTideApi, None],
):
    websession = websession_factory(status, tide_xml_str)
    api = api_factory(websession=websession)
    await api.update()
    assert isinstance(api.tide_extremes, expected_tidetype)
    assert isinstance(api.tide_series, expected_tidetype)


async def test_api_next_extreme(api):
    """Test valid next tidal time returned"""
    await api.update()
    assert isinstance(api.next_extreme[0], datetime)
    assert isinstance(api.next_extreme[1], str)
    assert isinstance(api.next_extreme[2], float)


async def test_api_current_waterlevel(api):
    await api.update()
    assert isinstance(api.current_waterlevel, float)


async def test_waterlevel_series(api):
    await api.update()
    series = api.waterlevel_series

    # Check equal number of timestamps and waterlevels
    assert len(series["timestamp"]) == len(series["waterlevel"])

    # Check all values are of correct type
    for key, value_type in [("timestamp", datetime), ("waterlevel", float)]:
        assert all([isinstance(value, value_type) for value in series[key]])
