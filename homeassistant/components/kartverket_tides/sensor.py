from datetime import datetime, timedelta
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import Throttle

from homeassistant.components.kartverket_tides.api import (
    KartverketTideApi,
    KystverketTideData,
)
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    LENGTH_CM,
)
from homeassistant.components.kartverket_tides.validators import (
    tide_interval,
    tide_language,
)


_LOGGER = logging.getLogger(__name__)


CONF_INTERVAL = "tide_interval"
CONF_LANG = "tide_language"
CONF_ENABLE_UTC = "tide_enable_utc"
ATTR_NEXT_HIGH_TIME = "next_high_time"
ATTR_NEXT_HIGH_LEVEL = "next_high_level"
ATTR_NEXT_LOW_TIME = "next_low_time"
ATTR_NEXT_LOW_LEVEL = "next_low_level"
ATTR_INCREASING_TEXT = "increasing_text"

ATTRIBUTION = "Data provided by Kartverket under NLOD"
DEFAULT_NAME = "Kartverket Tides"
DEFAULT_ICON_KEY = "flow"
SCAN_INTERVAL = timedelta(hours=2)

ICONS = {
    "ebb": "mdi:waves-arrow-left",
    "flow": "mdi:waves-arrow-right",
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_LATITUDE): cv.latitude,
        vol.Required(CONF_LONGITUDE): cv.longitude,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_INTERVAL, default=10): vol.All(
            vol.Coerce(int), tide_interval
        ),
        vol.Optional(CONF_LANG, default="en"): vol.All(vol.Coerce(str), tide_language),
        vol.Optional(CONF_ENABLE_UTC, default=0): cv.boolean,
    }
)


utc_enabled = False


def _time(dt: datetime) -> datetime:
    """Return time as local or UTC as configured for sensor"""
    fmt = "%H:%M"
    if utc_enabled:
        return dt_util.as_utc(dt).strftime(fmt)
    else:
        return dt_util.as_local(dt).strftime(fmt)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Entur public transport sensor."""
    global utc_enabled

    name = config.get(CONF_NAME)
    lat = config.get(CONF_LATITUDE)
    lon = config.get(CONF_LONGITUDE)
    interval = config.get(CONF_INTERVAL)
    lang = config.get(CONF_LANG)

    if config.get(CONF_ENABLE_UTC):
        utc_enabled = True

    init_client = KartverketTideApi(
        lat, lon, interval, lang, web_session=async_get_clientsession(hass),
    )

    await init_client.update()

    proxy_client = KartverketProxy(init_client)

    async_add_entities([KartverketTideSensor(proxy_client, name)], True)


class KartverketProxy:
    """Karverket API client proxy

    Ensure thottling of API

    The client currently does not check for rate limits, as they do not appear to be available.
    """

    def __init__(self, api: KartverketTideApi):
        self._api = api

    @Throttle(SCAN_INTERVAL)
    async def async_update(self) -> None:
        """Update data in client"""
        await self._api.update()


class KartverketTideSensor(SensorEntity):
    """Implementation of Kartverket tide data sensor."""

    def __init__(self, api: KartverketTideApi, name: str) -> None:
        """Initialize the sensor."""
        self.api = api
        self._name = name
        self._state: int | None = None
        self._icon = ICONS[DEFAULT_ICON_KEY]
        self._attributes: dict[str, str] = {}

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        self._attributes[ATTR_ATTRIBUTION] = ATTRIBUTION
        return self._attributes

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit this state is expressed in."""
        return LENGTH_CM

    @property
    def icon(self) -> str:
        """Icon to use in the frontend."""
        return self._icon

    async def async_update(self) -> None:
        """Get the latest data and update the states."""
        await self.api.async_update()

        self._attributes = {}

        data: KystverketTideData = self.api.get_tide_data()
        if data is None:
            self._state = None
            return

        self._state = self.api.current_waterlevel

        extreme_waterlevels = self.tide_extremes.data[0].waterlevels
        if extreme_waterlevels[0].flag == "low":
            next_low = extreme_waterlevels[0]
            next_high = extreme_waterlevels[1]
        else:
            next_low = extreme_waterlevels[1]
            next_high = extreme_waterlevels[0]

        self._attributes[ATTR_NEXT_HIGH_TIME] = _time(next_high.time)
        self._attributes[ATTR_NEXT_HIGH_LEVEL] = next_high.value

        self._attributes[ATTR_NEXT_LOW_TIME] = _time(next_low.time)
        self._attributes[ATTR_NEXT_LOW_LEVEL] = next_low.value

        increasing_key = "flood" if self.api.is_increasing else "ebb"
        self._icon = ICONS[increasing_key]
        self._attributes[ATTR_INCREASING_TEXT] = f"{increasing_key.capitalize()}ing"

        waterlevels = self.tide_series.data[0].waterlevels
        for i, level in enumerate(waterlevels):
            self._attributes[
                f"waterlevel_#{i}"
            ] = f"{_time(level.time)} {level.value}cm"
