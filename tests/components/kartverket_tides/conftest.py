from pathlib import Path
from xml.etree import ElementTree
from typing import Callable
from unittest.mock import patch

import pytest

from homeassistant.helpers.aiohttp_client import DATA_CLIENTSESSION
from homeassistant.components.kartverket_tides.api import KartverketTideApi
from tests.components.kartverket_tides.const import LATITUDE, LONGITUDE, LANG, INTERVAL


@pytest.fixture
def websession_factory(hass):
    def wrapper(status: int, body: dict):
        class MockResponse:
            """Test response."""

            def __init__(self):
                """Test response init."""
                self.status = status
                self.headers = {"Content-Type": "sometype"}

            @property
            def body(self):
                """Test response body."""
                return body

            async def release(self):
                """Test response release."""
                pass

        class MockWebsession:
            """Test websession with context management"""

            class get:
                def __init__(self, url: str, params: dict):
                    """Test websession get."""
                    pass

                async def __aenter__(self):
                    return MockResponse()

                async def __aexit__(self, exc_type, exc, tb):
                    return

            def detach(self):
                """Test websession detach."""

        websession = MockWebsession()
        hass.data[DATA_CLIENTSESSION] = websession

        return websession

    return wrapper


@pytest.fixture
def test_path():
    """Path of current test directory"""
    return Path(__file__).parent


@pytest.fixture
def tide_xml_str(test_path):
    """Example tide data as XML string"""
    with Path(test_path, "example_data.xml").open() as fh:
        return fh.read()


@pytest.fixture
def tide_xml_etree(tide_xml_str: str) -> ElementTree:
    """Example tide data as XML ElementTree"""
    return ElementTree.fromstring(tide_xml_str)


@pytest.fixture
def mock_clientsession():
    with patch(
        "homeassistant.components.kartverket_tides.api.ClientSession"
    ) as _mock_clientsession:
        yield _mock_clientsession


@pytest.fixture
def mock_asyncio_run():
    with patch(
        "homeassistant.components.kartverket_tides.api.asyncio_run"
    ) as _mock_asyncio_run:
        yield _mock_asyncio_run


@pytest.fixture
def api_factory(aioclient_mock, mock_clientsession, mock_asyncio_run):
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
def api(
    api_factory, websession_factory: Callable, tide_xml_str: str,
):
    """KartverketApi with default test values"""
    websession = websession_factory(200, tide_xml_str)
    return api_factory(websession=websession)
