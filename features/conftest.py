"""Fixtures and steps shared by the pytest-bdd scenarios (BDD scenarios §2.2).

Feature files go in features/<area>/, copied from BEHAVIOR_DRIVEN_DEVELOPMENT_SCENARIOS.md,
and their step definitions in features/steps/. Each phase of IMPLEMENTATION_GUIDE.md binds
the features it makes pass.
"""

import pytest

from tests import factories


@pytest.fixture
def travel_request():
    """The scenario's travel request: "a valid travel request" until a step changes a field."""
    return factories.valid_request()
