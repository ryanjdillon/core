from pathlib import Path
from xml.etree import ElementTree

import pytest

from homeassistant.helpers.aiohttp_client import DATA_CLIENTSESSION


@pytest.fixture
def websession_factory(hass):
    def wrapper(status: int, body: dict):
        class MockResponse:
            """Test response."""

            def __init__(self):
                """Test response init."""
                self.status = status
                self.headers = {"Content-Type": "sometype"}

            async def body(self):
                """Test response body."""
                return body

            async def release(self):
                """Test response release."""

        class MockWebsession:
            """Test websession with context management"""

            def __enter__(self):
                return self

            async def get(self, url):
                """Test websession get."""
                return MockResponse()

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
