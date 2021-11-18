from typing import Any, Iterable

# TODO use api enums
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
