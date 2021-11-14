from datetime import timedelta
from typing import Any, Iterable

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import Throttle

from homeassistant.components.kartverket_tides.api import KartverketTideApi

DEFAULT_NAME = "Kartverket Tides"
DEFAULT_ICON_KEY = "flow"

ICONS = {
    "ebb": "mdi:waves-arrow-left",
    "flow": "mdi:waves-arrow-right",
}

TIDE_INTERVALS = (10, 60)
TIDE_LANGUAGES = {"bokmal": "nb", "nynorsk": "nn", "english": "en"}
TIDE_UNITS = {"mm": 1, "cm": 10, "m": 1000, "in": 0.0393700787, "ft": 0.0032808399}


def mm_to_unit(mm: float, output_unit: str) -> float:
    """Convert default API unit of 'mm' to specified output unit"""
    return mm * TIDE_UNITS[output_unit]


def contains_value(name: str, value: Any, iterable: Iterable[Any]) -> bool:
    """Check that a value is contained in an iterable"""
    if value in iterable:
        return value
    raise vol.Invalid(f"invalid {name}. Must be one of {', '.join(iterable)}.")


def tide_interval(interval: int) -> int:
    """Validate user's 'interval' configuration value"""
    return contains_value("tide interval", interval, TIDE_INTERVALS)


def tide_unit(unit: str) -> str:
    """Validate user's 'unit' configuration value"""
    return contains_value("tide unit", unit, TIDE_UNITS.keys())


def tide_language(language: str) -> str:
    """Validate user's 'language' configuration value"""
    return contains_value("tide language", language, TIDE_LANGUAGES.keys())


# TODO think about this, only really need to scan every so often then round-robin times
SCAN_INTERVAL = timedelta(hours=2)

# CONF
# unit: in, cm, m, ft
# latlon: optional, if not provided, use current if present
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_LAT): cv.latitude,
        vol.Optional(CONF_LON): cv.longitude,
        vol.Optional(CONF_INTERVAL, default=10): vol.All(
            vol.Coerce(int), tide_interval
        ),
        vol.Optional(CONF_UNIT, default="mm"): vol.All(vol.Coerce(str), tide_unit),
        vol.Optional(CONF_LANG, default="nb"): vol.All(vol.Coerce(str), tide_unit),
        vol.Optional(CONF_TZONE, default=1): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=1)
        ),
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Entur public transport sensor."""

    name = config.get(CONF_NAME)
    lat = config.get(CONF_LAT)
    lon = config.get(CONF_LON)
    tzone = config.get(CONF_TZONE)
    interval = config.get(CONF_INTERVAL)
    unit = config.get(CONF_UNIT)
    lang = config.get(CONF_LANG)

    init_client = KartverketTideApi(
        lat,
        lon,
        tzone,
        interval,
        unit,
        lang,
        web_session=async_get_clientsession(hass),
    )

    await init_client.update()

    proxy_client = KartverketProxy(init_client)

    async_add_entities([KartverketTideSensor(proxy_client, name)], True)


class KartverketProxy:
    """Karverket API client proxy

    Ensure thottling of API. However, currently the API client does not check
    rate limits, as they do not appear to be available.
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
        #TODO flag/icon, low/high
        return self

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit this state is expressed in."""
        return TIME_MINUTES

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

        # TODO next states should be (value, time)
        self._state = due_in_minutes(waterlevels[0].expected_departure_time)

        self._attributes[ATTR_ROUTE] = waterlevels[0].front_display
        self._attributes[ATTR_ROUTE_ID] = waterlevels[0].line_id

        # TODO set next time/value/flag(icon)
        # TODO if next tide high (flood), if low (ebb)
        self._icon = ICONS.get(waterlevels[0].flag, ICONS[DEFAULT_ICON_KEY])

        # TODO For waterlevels
        for i, level in enumerate(waterlevels):
            self._attributes[f"waterlevel_#{i}"] = (
                f"{'' if bool(level.is_realtime) else 'ca. '}"
                f"{level.expected_departure_time.strftime('%H:%M')} {level.front_display}"
            )
