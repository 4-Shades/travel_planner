"""Fixtures for the unit and service tests (TDD plan §2.4). settings and agent_app are in the root conftest.py."""

import pytest
from freezegun import freeze_time

from tests import factories


@pytest.fixture
def valid_request():
    """Factory for valid travel request bodies: valid_request(budget=0)."""
    return factories.valid_request


@pytest.fixture
def today():
    """Start the clock at the plan's reference date.

    The clock keeps ticking, because asyncio's timers (timeouts, sleeps) never fire on a stopped clock.
    """
    with freeze_time(factories.TODAY, tick=True) as frozen:
        yield frozen
