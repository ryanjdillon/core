from datetime import timedelta


ATTRIBUTION = "Data provided by Kartverket under NLOD"
DEFAULT_NAME = "Kartverket Tides"
DEFAULT_ICON_KEY = "flow"
SCAN_INTERVAL = timedelta(hours=2)

ATTR_NEXT_HIGH_TIME = "next_high_time"
ATTR_NEXT_HIGH_LEVEL = "next_high_level"
ATTR_NEXT_LOW_TIME = "next_low_time"
ATTR_NEXT_LOW_LEVEL = "next_low_level"
ATTR_INCREASING_TEXT = "increasing_text"

CONF_INTERVAL = "tide_interval"
CONF_LANG = "tide_language"
CONF_ENABLE_UTC = "tide_enable_utc"

ICONS = {
    "ebb": "mdi:waves-arrow-left",
    "flow": "mdi:waves-arrow-right",
}
