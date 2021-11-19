"""The test for the zodiac sensor platform."""
from datetime import datetime
from typing import Callable, List
from unittest.mock import MagicMock

import pytest
import pytz

from homeassistant.const import (
    CONF_NAME,
    CONF_LATITUDE,
    CONF_LONGITUDE,
)
from homeassistant.components.kartverket_tides.api import KartverketTideApi
from homeassistant.components.kartverket_tides.const import (
    CONF_INTERVAL,
    CONF_LANG,
    ATTR_INCREASING_TEXT,
    ATTR_NEXT_LOW_LEVEL,
    ATTR_NEXT_LOW_TIME,
    ATTR_NEXT_HIGH_LEVEL,
    ATTR_NEXT_HIGH_TIME,
    ICONS,
)
from homeassistant.components.kartverket_tides.data import (
    KartverketTideData,
    TideLocation,
    TideData,
    TideWaterLevel,
)
from homeassistant.components.kartverket_tides.sensor import (
    KartverketTideApi,
    async_setup_platform,
)

from tests.components.kartverket_tides.const import (
    TEST_CONF_INTERVAL,
    TEST_CONF_LATITUDE,
    TEST_CONF_LONGITUDE,
    TEST_CONF_NAME,
    TEST_CONF_LANG,
)
from tests.common import MockEntityPlatform


@pytest.fixture
def location():
    return TideLocation(
        name="test-name",
        code="TST",
        latitude=61.0,
        longitude=10.0,
        delay=10,
        factor=1,
        obsname="obs-name",
        obscode="OBS",
        descr="location descr",
    )


@pytest.fixture
def extreme_waterlevels():
    return [
        TideWaterLevel(
            time=datetime(2021, 1, 1, 1, 0, 0, tzinfo=pytz.UTC),
            value="10.0",
            flag="low",
        ),
        TideWaterLevel(
            time=datetime(2021, 1, 1, 6, 0, 0, tzinfo=pytz.UTC),
            value="20.0",
            flag="high",
        ),
    ]


@pytest.fixture
def series_waterlevels():
    return [
        TideWaterLevel(
            time=datetime(2021, 1, 1, 0, 0, 0, tzinfo=pytz.UTC), value="9.0",
        ),
        TideWaterLevel(
            time=datetime(2021, 1, 1, 1, 0, 0, tzinfo=pytz.UTC), value="10.0",
        ),
    ]


@pytest.fixture
def tide_data_factory(location):
    def tide_data(tide_waterlevels: List[TideWaterLevel]):
        return KartverketTideData(
            location=location,
            reflevelcode="TST",
            data=TideData(type="type", unit="cm", waterlevels=tide_waterlevels,),
        )

    return tide_data


@pytest.fixture
def tide_extremes(
    tide_data_factory: Callable, extreme_waterlevels: List[TideWaterLevel]
):
    return tide_data_factory(extreme_waterlevels)


@pytest.fixture
def tide_series(tide_data_factory: Callable, series_waterlevels: List[TideWaterLevel]):
    return tide_data_factory(series_waterlevels)


@pytest.fixture
def mock_kartverkettideapi(
    tide_extremes: KartverketTideData, tide_series: KartverketTideData
):
    MockKartVerketApi = MagicMock(autospec=KartverketTideApi)
    api = MockKartVerketApi()
    api.tide_extremes.return_value = tide_extremes
    api.tide_series.return_value = tide_series
    api.current_level.return_value = 42.0
    api.is_increasing.return_value = True
    return api


async def test_kartveket_state(hass, mock_kartverkettideapi: MagicMock):
    """Test the Kartverket Tide sensor."""
    config = {
        CONF_NAME: TEST_CONF_NAME,
        CONF_LATITUDE: TEST_CONF_LATITUDE,
        CONF_LONGITUDE: TEST_CONF_LONGITUDE,
        CONF_INTERVAL: TEST_CONF_INTERVAL,
        CONF_LANG: TEST_CONF_LANG,
    }
    platform = MockEntityPlatform(hass)

    assert await async_setup_platform(
        hass, config, platform.async_add_entities, discovery_info=None
    )
    await hass.async_block_till_done()

    state = hass.states.get("sensor.kartverket_tides")

    assert state.state == 9.0

    assert state.icon == ICONS["ebb"]

    assert state.attributes[ATTR_NEXT_LOW_TIME] == "2021-01-01T00:00:00+00:00"
    assert state.attributes[ATTR_NEXT_LOW_LEVEL] == 10.0
    assert state.attributes[ATTR_NEXT_HIGH_TIME] == "2021-01-01T00:06:00+00:00"
    assert state.attributes[ATTR_NEXT_HIGH_LEVEL] == 20.0
    assert state.attributes[ATTR_INCREASING_TEXT] == "Ebbing"
