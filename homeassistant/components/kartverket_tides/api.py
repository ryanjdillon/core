from asyncio import run as asyncio_run
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, IntEnum
from xml.etree import ElementTree
from typing import Any, Dict, List, Optional, Union, Tuple

from aiohttp import ClientSession
import async_timeout

from homeassistant.components.kartverket_tides.data import (
    KartverketTideData,
    parse_tide_data,
)

_LOGGER = logging.getLogger(__name__)


class EnumAttribute:
    """General descriptor for validated Enum attributes"""

    __slots__ = ("_attr", "_Enum")

    def __init__(self, attr: str, enum: Enum):
        self._attr = attr
        self._Enum = enum

    def __get__(self, obj: object, objtype: type):
        return obj.__dict__[self._attr]

    def __set__(self, obj: object, enum_member: Any):
        enum_members = self._Enum.__members__.values()
        if enum_member not in enum_members:
            value_strings = [f"{str(v)} ({v.value})" for v in enum_members]
            raise ValueError(
                f"Invalid value '{str(enum_member)}' for attribute `{self._attr}` "
                f"must be one of: {', '.join(value_strings)}"
            )
        obj.__dict__[self._attr] = enum_member.value


class Interval(IntEnum):
    LOW = 10
    HIGH = 60


class Language(Enum):
    NB = "nb"  # bokmål
    NN = "nn"  # nynorsk
    EN = "en"  # english


class KartverketTideApi:
    """Kartveket tide data API"""

    BASE_URL = "https://api.sehavniva.no/tideapi.php?"

    interval = EnumAttribute("interval", Interval)
    lang = EnumAttribute("lang", Language)

    tide_series: KartverketTideData = None
    tide_extremes: KartverketTideData = None

    def __init__(
        self,
        lat: float,
        lon: float,
        interval: int,
        lang: str,
        websession: Optional[ClientSession] = None,
    ):
        if websession is None:

            async def _create_session() -> ClientSession:
                return ClientSession()

            self.websession = asyncio_run(_create_session())
            # TODO remove
            #loop = asyncio.get_event_loop() # should rather be get_running_loop()
            #self.websession = asyncio.run(loop.run_until_complete(_create_session())
        else:
            self.websession = websession

        self.lat = lat
        self.lon = lon
        self.interval = interval
        self.lang = lang

    @property
    def next_extreme(self) -> Tuple[datetime, str, float]:
        """Time, flag, and value at next tidal extreme"""
        extreme = self.tide_extremes.data[0].waterlevels[0]
        return datetime.fromisoformat(extreme.time), extreme.flag, float(extreme.value)

    @property
    def current_waterlevel(self) -> float:
        """State of next tide: high or low"""
        return float(self.tide_series.data[0].waterlevels[0].value)

    @property
    def waterlevel_series(self) -> Dict[str, Union[datetime, float]]:
        """Waterlevel timestamps and values"""
        timestamps = list()
        values = list()
        for waterlevel in self.tide_series.data[0].waterlevels:
            timestamps.append(datetime.fromisoformat(waterlevel.time))
            values.append(float(waterlevel.value))
        return {"timestamp": timestamps, "waterlevel": values}

    @property
    def is_increasing(self) -> bool:
        """Is tide increasing, i.e. flooding"""
        return self.next_tidal_low > self.next_tidal_high

    async def update(self) -> None:
        """Get the latest data from Kartverket tide API"""

        # Call with datatype param for upcoming waterlevel series
        self.tide_series = await self.update_by_datatype("all")

        # Call with datatype param for high/low extremes
        self.tide_extremes = await self.update_by_datatype("tab")

    async def close_connection(self) -> None:
        """Close the aiohttp session."""
        await self.websession.close()

    async def update_by_datatype(self, datatype: str) -> None:
        """Call Kystverket tides API with specified datatype"""
        datatypes = ("all", "tab")
        if datatype not in datatypes:
            raise ValueError(
                f"URL param `datatype` must be one of {', '.join(datatypes)}"
            )

        api_params = {
            "lat": self.lat,
            "lon": self.lon,
            "lang": self.lang,
            "interval": self.interval,
            "datatype": datatype,
            "fromtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+%Z"),
            "tzone": 0,
            "dst": 0,
            "tide_request": "locationdata",
        }

        with async_timeout.timeout(15):
            async with self.websession.get(
                self.BASE_URL, params=api_params
            ) as response:
                if response.status != 200:
                    _LOGGER.error(
                        "Error retrieving tide data, response http status code: %s",
                        response.status,
                    )
                    return
                return parse_tide_data(ElementTree.fromstring(response.body))
