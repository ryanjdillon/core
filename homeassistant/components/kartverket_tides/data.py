from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from xml.etree import ElementTree


@dataclass
class TideWaterLevel:
    value: str
    time: datetime
    flag: Optional[str] = None


@dataclass
class TideLocation:
    name: str
    code: str
    latitude: float
    longitude: float
    delay: int
    factor: float
    obsname: str
    obscode: str
    descr: str


@dataclass
class TideData:
    type: str
    unit: str
    waterlevels: List[TideWaterLevel]


@dataclass
class KartverketTideData:
    location: TideLocation
    reflevelcode: str
    data: List[TideData]


def parse_tide_data(tide_tree: ElementTree) -> KartverketTideData:
    """Parse tide XML data to dataclass"""

    LOCATION_ATTRS = (
        "name",
        "code",
        "latitude",
        "longitude",
        "delay",
        "factor",
        "obsname",
        "obscode",
        "descr",
    )

    WATERLEVEL_ATTRS = ("value", "time", "flag")

    def _parse_data(data_tree: ElementTree) -> TideData:
        """Parse data field and child waterlevel fields"""
        waterlevels = [
            TideWaterLevel(**{k: wl.get(k) for k in WATERLEVEL_ATTRS})
            for wl in data_tree.findall("waterlevel")
        ]
        return TideData(
            type=data_tree.get("type"),
            unit=data_tree.get("unit"),
            waterlevels=waterlevels,
        )

    locationdata_tree = tide_tree.find("locationdata")
    location_tree = locationdata_tree.find("location")
    data_tree_list = locationdata_tree.findall("data")

    return KartverketTideData(
        location=TideLocation(**{k: location_tree.get(k) for k in LOCATION_ATTRS}),
        reflevelcode=locationdata_tree.find("reflevelcode"),
        data=[_parse_data(data_tree) for data_tree in data_tree_list],
    )
