"""Data contracts between services (TDD plan, iteration 1)."""

import uuid

import pytest
from pydantic import ValidationError

from shared import schemas
from tests import factories


def error_fields(excinfo):
    return {str(part) for error in excinfo.value.errors() for part in error["loc"]}


def parse_request(body):
    return schemas.TravelRequest.model_validate(body)


def assert_rejected(body, field):
    with pytest.raises(ValidationError) as excinfo:
        parse_request(body)
    assert field in error_fields(excinfo)


# SCH-01 (TP-SRS-050)
def test_valid_request_is_accepted(valid_request):
    request = parse_request(valid_request())
    assert request.destination == "Tokyo"


# SCH-02 (TP-SRS-050)
@pytest.mark.parametrize("field", ["origin", "destination"])
@pytest.mark.parametrize("length, accepted", [(1, False), (2, True), (120, True), (121, False)])
def test_place_name_length_limits(valid_request, field, length, accepted):
    body = valid_request(**{field: "a" * length})
    if accepted:
        assert len(getattr(parse_request(body), field)) == length
    else:
        assert_rejected(body, field)


# SCH-03 (TP-SRS-050)
@pytest.mark.parametrize("end_date, accepted", [("2026-12-05", False), ("2026-12-06", False), ("2026-12-07", True)])
def test_end_date_must_be_after_start_date(valid_request, end_date, accepted):
    body = valid_request(start_date="2026-12-06", end_date=end_date)
    if accepted:
        parse_request(body)
    else:
        assert_rejected(body, "end_date")


# SCH-04 (TP-SRS-050)
@pytest.mark.parametrize("budget, accepted", [(0, False), (-1, False), (0.01, True)])
def test_budget_must_be_positive(valid_request, budget, accepted):
    body = valid_request(budget=budget)
    if accepted:
        assert parse_request(body).budget == budget
    else:
        assert_rejected(body, "budget")


# SCH-05 (TP-SRS-050)
@pytest.mark.parametrize("travellers, accepted", [(0, False), (1, True), (9, True), (10, False)])
def test_travellers_limits(valid_request, travellers, accepted):
    body = valid_request(travellers=travellers)
    if accepted:
        assert parse_request(body).travellers == travellers
    else:
        assert_rejected(body, "travellers")


# SCH-06 (TP-SRS-050, TP-SRS-172)
@pytest.mark.parametrize("currency", ["US", "USDD", "U5D"])
def test_currency_must_be_three_letters(valid_request, currency):
    assert_rejected(valid_request(currency=currency), "currency")


# SCH-06 (TP-SRS-050, TP-SRS-172)
@pytest.mark.parametrize("currency", ["EUR", "eur"])
def test_three_letter_currency_is_accepted(valid_request, currency):
    parse_request(valid_request(currency=currency))


# SCH-07 (TP-SRS-050)
@pytest.mark.parametrize("count, accepted", [(20, True), (21, False)])
def test_preferences_limit(valid_request, count, accepted):
    body = valid_request(preferences=[f"interest {n}" for n in range(count)])
    if accepted:
        assert len(parse_request(body).preferences) == count
    else:
        assert_rejected(body, "preferences")


# SCH-08 (TP-SRS-050)
@pytest.mark.parametrize("length, accepted", [(128, True), (129, False)])
def test_user_id_length_limit(valid_request, length, accepted):
    body = valid_request(user_id="u" * length)
    if accepted:
        parse_request(body)
    else:
        assert_rejected(body, "user_id")


# SCH-08 (TP-SRS-050)
def test_user_id_is_optional(valid_request):
    assert parse_request(valid_request()).user_id is None


# SCH-09 (TP-SRS-051)
@pytest.mark.parametrize("field", ["origin", "destination"])
def test_repeated_spaces_are_collapsed(valid_request, field):
    request = parse_request(valid_request(**{field: "San   Francisco"}))
    assert getattr(request, field) == "San Francisco"


# SCH-10 (TP-SRS-051)
def test_currency_is_upper_cased(valid_request):
    assert parse_request(valid_request(currency="eur")).currency == "EUR"


# SCH-11 (TP-SRS-052)
def test_missing_ids_are_generated(valid_request):
    first = parse_request(valid_request())
    second = parse_request(valid_request())
    for value in (first.request_id, first.trip_id, second.request_id, second.trip_id):
        uuid.UUID(value)
    assert first.request_id != second.request_id
    assert first.trip_id != second.trip_id


# SCH-12 (TP-SRS-052)
def test_given_ids_are_kept(valid_request):
    request = parse_request(valid_request(request_id="req-42", trip_id="trip-42"))
    assert (request.request_id, request.trip_id) == ("req-42", "trip-42")


# SCH-13 (TP-SRS-053)
def test_currency_defaults_to_usd(valid_request):
    assert parse_request(valid_request()).currency == "USD"


# SCH-14 (TP-SRS-172)
@pytest.mark.parametrize("value", ["01/12/2026", "2026/12/01", "20261201", 1796083200])
def test_dates_must_use_iso_8601(valid_request, value):
    assert_rejected(valid_request(start_date=value), "start_date")


# SCH-14 (TP-SRS-172)
def test_dates_serialize_as_iso_8601(valid_request):
    dumped = parse_request(valid_request()).model_dump(mode="json")
    assert (dumped["start_date"], dumped["end_date"]) == ("2026-12-01", "2026-12-06")


# SCH-15 (TP-SRS-062)
def test_trip_plan_fields():
    assert set(schemas.TripPlan.model_fields) == {
        "request_id",
        "trip_id",
        "flights",
        "stay",
        "activities",
        "errors",
        "sources",
    }


# SCH-15: an errors entry names its part and has a message.
@pytest.mark.parametrize("part", ["flights", "stay", "activities"])
def test_part_error_names_part(part):
    error = schemas.PartError(part=part, message="Service is temporarily unavailable.")
    assert error.part == part


def test_part_error_rejects_unknown_part():
    with pytest.raises(ValidationError):
        schemas.PartError(part="trains", message="Service is temporarily unavailable.")


# SCH-16 (TP-SRS-070)
@pytest.mark.parametrize("service", schemas.SPECIALISTS)
def test_specialist_response_needs_offers_or_error(service):
    contract = schemas.SPECIALISTS[service]
    offer = factories.OFFERS[service]()
    with pytest.raises(ValidationError):
        contract.response.model_validate({contract.part: [], "sources": []})
    contract.response.model_validate({contract.part: [offer]})
    contract.response.model_validate({contract.part: [], "error": "Planner is temporarily unavailable."})


# SCH-17 (TP-SRS-074)
@pytest.mark.parametrize("service", schemas.SPECIALISTS)
@pytest.mark.parametrize(
    "overrides, accepted",
    [({"price": -0.01}, False), ({"price": 0}, True), ({"currency": "US"}, False), ({"currency": "usd"}, True)],
)
def test_offer_price_and_currency(service, overrides, accepted):
    contract = schemas.SPECIALISTS[service]
    body = {contract.part: [factories.OFFERS[service](**overrides)]}
    if accepted:
        contract.response.model_validate(body)
    else:
        with pytest.raises(ValidationError):
            contract.response.model_validate(body)


# SCH-18 (TP-SRS-089, TP-SRS-170)
@pytest.mark.parametrize("field", ["title", "url", "license"])
def test_source_requires_title_url_license(field):
    entry = factories.source()
    del entry[field]
    with pytest.raises(ValidationError):
        schemas.Source.model_validate(entry)
    with pytest.raises(ValidationError):
        schemas.Source.model_validate({**factories.source(), field: ""})


# SCH-19 (TP-SRS-090)
def property_names(schema):
    if isinstance(schema, dict):
        yield from schema.get("properties", {})
        for value in schema.values():
            yield from property_names(value)
    elif isinstance(schema, list):
        for value in schema:
            yield from property_names(value)


@pytest.mark.parametrize("service", schemas.SPECIALISTS)
def test_model_schema_has_no_sources_field(service):
    schema = schemas.SPECIALISTS[service].model_output.model_json_schema()
    names = set(property_names(schema))
    assert schemas.SPECIALISTS[service].part in names
    assert "sources" not in names
