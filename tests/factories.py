"""Test data shared by tests/ and features/ (TDD plan §2.4)."""

TODAY = "2026-10-24"


def valid_request(**overrides):
    """Return a valid travel request body; overrides replace or add single fields."""
    request = {
        "origin": "Manila",
        "destination": "Tokyo",
        "start_date": "2026-12-01",
        "end_date": "2026-12-06",
        "budget": 1500,
        "travellers": 2,
    }
    request.update(overrides)
    return request
