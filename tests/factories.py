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


def flight_offer(**overrides):
    offer = {
        "airline": "Example Air",
        "route": "MNL to HND",
        "departure_date": "2026-12-01",
        "return_date": "2026-12-06",
        "price": 420,
        "currency": "USD",
        "notes": "Illustrative round-trip fare",
    }
    offer.update(overrides)
    return offer


def stay_offer(**overrides):
    offer = {
        "name": "Example Hotel Shinjuku",
        "area": "Shinjuku",
        "nights": 5,
        "price": 900,
        "currency": "USD",
        "notes": "Close to the station",
    }
    offer.update(overrides)
    return offer


def activity_offer(**overrides):
    offer = {
        "name": "Senso-ji Temple",
        "description": "Tokyo's oldest temple, in Asakusa",
        "price": 0,
        "currency": "USD",
        "notes": "Free entry",
    }
    offer.update(overrides)
    return offer


OFFERS = {"flight": flight_offer, "stay": stay_offer, "activities": activity_offer}


def source(**overrides):
    entry = {
        "title": "Tokyo",
        "url": "https://en.wikivoyage.org/wiki/Tokyo",
        "license": "CC BY-SA 4.0",
    }
    entry.update(overrides)
    return entry
