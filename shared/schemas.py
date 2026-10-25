"""Data contracts between all services, defined once here (TP-SRS-162)."""

import re
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl, StringConstraints, field_validator, model_validator

Part = Literal["flights", "stay", "activities"]

# ISO 4217 three-letter code, upper-cased (TP-SRS-050, TP-SRS-051, TP-SRS-172).
Currency = Annotated[str, StringConstraints(pattern=r"^[A-Za-z]{3}$", to_upper=True)]
Text = Annotated[str, StringConstraints(min_length=1)]
Price = Annotated[float, Field(ge=0, allow_inf_nan=False)]

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _iso_date(value):
    """Accept only YYYY-MM-DD strings or date objects (TP-SRS-172)."""
    if isinstance(value, date) or (isinstance(value, str) and _ISO_DATE.match(value)):
        return value
    raise ValueError("Date must use the format YYYY-MM-DD")


def _new_id():
    return str(uuid.uuid4())


class TravelRequest(BaseModel):
    origin: Annotated[str, StringConstraints(min_length=2, max_length=120)]
    destination: Annotated[str, StringConstraints(min_length=2, max_length=120)]
    start_date: date
    end_date: date
    budget: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    travellers: Annotated[int, Field(ge=1, le=9)]
    currency: Currency = "USD"
    preferences: Annotated[list[str], Field(max_length=20)] = []
    user_id: Annotated[str, StringConstraints(max_length=128)] | None = None
    request_id: Text = Field(default_factory=_new_id)
    trip_id: Text = Field(default_factory=_new_id)

    @field_validator("origin", "destination", mode="before")
    @classmethod
    def _collapse_spaces(cls, value):
        if isinstance(value, str):
            return re.sub(r" {2,}", " ", value).strip()
        return value

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _check_iso_date(cls, value):
        return _iso_date(value)

    @field_validator("end_date")
    @classmethod
    def _end_after_start(cls, value, info):
        start = info.data.get("start_date")
        if start is not None and value <= start:
            raise ValueError("End date must be after the start date")
        return value


class FlightOffer(BaseModel):
    airline: Text
    route: Text
    departure_date: date
    return_date: date | None
    price: Price
    currency: Currency
    notes: str


class StayOffer(BaseModel):
    name: Text
    area: Text
    nights: Annotated[int, Field(ge=1)]
    price: Price
    currency: Currency
    notes: str


class ActivityOffer(BaseModel):
    name: Text
    description: Text
    price: Price
    currency: Currency
    notes: str


class Source(BaseModel):
    title: Text
    url: HttpUrl
    license: Text


class PartError(BaseModel):
    part: Part
    message: Text


class _SpecialistResponse(BaseModel):
    """A specialist answers with at least one offer or an explicit error (TP-SRS-070)."""

    sources: list[Source] = []
    error: Text | None = None

    @model_validator(mode="after")
    def _offers_or_error(self):
        if not self.offers() and self.error is None:
            raise ValueError("A response needs at least one offer or an error")
        return self

    def offers(self):
        raise NotImplementedError


class FlightResponse(_SpecialistResponse):
    flights: list[FlightOffer] = []

    def offers(self):
        return self.flights


class StayResponse(_SpecialistResponse):
    stay: list[StayOffer] = []

    def offers(self):
        return self.stay


class ActivitiesResponse(_SpecialistResponse):
    activities: list[ActivityOffer] = []

    def offers(self):
        return self.activities


# What the language model is asked to produce. These have no field for sources,
# which come only from the guidance index (TP-SRS-090).
class FlightSuggestions(BaseModel):
    flights: list[FlightOffer]


class StaySuggestions(BaseModel):
    stay: list[StayOffer]


class ActivitySuggestions(BaseModel):
    activities: list[ActivityOffer]


class TripPlan(BaseModel):
    request_id: Text
    trip_id: Text
    flights: list[FlightOffer] = []
    stay: list[StayOffer] = []
    activities: list[ActivityOffer] = []
    errors: list[PartError] = []
    sources: list[Source] = []


@dataclass(frozen=True)
class SpecialistContract:
    part: Part
    response: type[_SpecialistResponse]
    model_output: type[BaseModel]


SPECIALISTS = {
    "flight": SpecialistContract("flights", FlightResponse, FlightSuggestions),
    "stay": SpecialistContract("stay", StayResponse, StaySuggestions),
    "activities": SpecialistContract("activities", ActivitiesResponse, ActivitySuggestions),
}
