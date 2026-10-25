"""Fixtures for the unit and service tests (TDD plan §2.4)."""

import pytest
from freezegun import freeze_time

from tests import factories


@pytest.fixture
def valid_request():
    """Factory for valid travel request bodies: valid_request(budget=0)."""
    return factories.valid_request


@pytest.fixture
def today():
    """Freeze the clock at the plan's reference date."""
    with freeze_time(factories.TODAY) as frozen:
        yield frozen
