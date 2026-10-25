"""Calling the three specialists at once and merging their answers into one trip plan (TP-SRS-060 to TP-SRS-065)."""

import asyncio
import logging

import httpx
from pydantic import ValidationError

from shared.request_id import current_request_id
from shared.schemas import SPECIALISTS, PartError, Source, TripPlan

SERVICE_UNAVAILABLE = "Service is temporarily unavailable."

logger = logging.getLogger("travel_planner.host")


class SpecialistFailed(Exception):
    """The specialist could not be reached, or did not give a valid answer."""


def service_urls(settings):
    return {
        "flight": settings.flight_service_url,
        "stay": settings.stay_service_url,
        "activities": settings.activities_service_url,
    }


def valid_sources(entries):
    """Keep the well-formed sources and drop the rest (TP-SRS-065)."""
    sources = []
    for entry in entries if isinstance(entries, list) else []:
        try:
            sources.append(Source.model_validate(entry))
        except ValidationError:
            logger.warning("Dropped a malformed source: %r", entry)
    return sources


async def ask(client, service, url, request, timeout):
    """Return one specialist's validated response, or raise SpecialistFailed."""
    try:
        # httpx limits each read, write, and connection to 5 seconds unless told otherwise; wait_for
        # limits the whole call, which may include several reads.
        response = await asyncio.wait_for(
            client.post(
                f"{url.rstrip('/')}/run",
                json=request.model_dump(mode="json"),
                headers={"X-Request-ID": current_request_id()},
                timeout=timeout,
            ),
            timeout,
        )
    except TimeoutError:
        raise SpecialistFailed(f"no answer within DOWNSTREAM_TIMEOUT_SECONDS ({timeout} s)") from None
    except httpx.HTTPError as error:
        raise SpecialistFailed(f"could not be reached: {type(error).__name__}") from None
    if response.status_code >= 400:
        raise SpecialistFailed(f"answered with HTTP {response.status_code}")
    try:
        body = response.json()
    except ValueError:
        raise SpecialistFailed("answered with invalid JSON") from None
    if not isinstance(body, dict):
        raise SpecialistFailed("answered with JSON that is not an object")
    # Sources are checked one by one, so one malformed source does not cost the whole part.
    sources = valid_sources(body.pop("sources", []))
    try:
        answer = SPECIALISTS[service].response.model_validate(body)
    except ValidationError as error:
        raise SpecialistFailed(f"answered with JSON that does not match its response model: {error}") from None
    return answer, sources


async def plan_trip(request, settings):
    """Return the merged trip plan; a failed specialist is reported in errors, never raised (TP-SRS-180)."""
    urls = service_urls(settings)
    timeout = settings.downstream_timeout_seconds
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *(ask(client, service, urls[service], request, timeout) for service in SPECIALISTS),
            return_exceptions=True,
        )

    plan = {"request_id": request.request_id, "trip_id": request.trip_id, "errors": [], "sources": {}}
    for service, result in zip(SPECIALISTS, results):
        part = SPECIALISTS[service].part
        if isinstance(result, BaseException):
            reason = str(result) if isinstance(result, SpecialistFailed) else f"{type(result).__name__}: {result}"
            logger.warning("The %s agent failed: %s", service, reason)
            plan[part] = []
            plan["errors"].append(PartError(part=part, message=SERVICE_UNAVAILABLE))
            continue
        answer, sources = result
        plan[part] = answer.offers()
        if answer.error:
            # The specialist's own message is already plain and safe to show (TP-SRS-031).
            plan["errors"].append(PartError(part=part, message=answer.error))
        for source in sources:
            # Duplicates are removed by URL, keeping the first (TP-SRS-065).
            plan["sources"].setdefault(str(source.url), source)
    plan["sources"] = list(plan["sources"].values())
    return TripPlan(**plan)
