"""FakeAgent: respx routes for the specialists' POST /run, used by Host tests (TDD plan §2.3)."""

import asyncio
import json

import httpx

from shared.schemas import SPECIALISTS
from tests import factories

AGENT_URLS = {"flight": "http://flight.test", "stay": "http://stay.test", "activities": "http://activities.test"}
# Environment that points the Host at the fakes.
AGENT_ENV = {
    "FLIGHT_SERVICE_URL": AGENT_URLS["flight"],
    "STAY_SERVICE_URL": AGENT_URLS["stay"],
    "ACTIVITIES_SERVICE_URL": AGENT_URLS["activities"],
}


def valid_response(service, sources=None):
    return {
        SPECIALISTS[service].part: [factories.OFFERS[service]()],
        "sources": [factories.source()] if sources is None else sources,
        "error": None,
    }


class FakeAgent:
    """A specialist that answers normally until told otherwise, recording every request."""

    def __init__(self, respx_mock, service):
        self.service = service
        self.part = SPECIALISTS[service].part
        self.route = respx_mock.post(f"{AGENT_URLS[service]}/run")
        self.answer_normally()

    def answer_normally(self, sources=None):
        self.answer(valid_response(self.service, sources))

    def answer(self, body, status=200):
        self.route.mock(return_value=httpx.Response(status, json=body))

    def answer_slowly(self, seconds):
        body = valid_response(self.service)

        async def slow(request):
            await asyncio.sleep(seconds)
            return httpx.Response(200, json=body)

        self.route.mock(side_effect=slow)

    def fail(self, status=500):
        self.answer({"detail": "fake failure"}, status=status)

    def answer_invalid_json(self):
        self.route.mock(return_value=httpx.Response(200, content=b'{"flights": [', headers={"Content-Type": "application/json"}))

    def answer_wrong_model(self):
        self.answer({self.part: [{"name": 42}], "sources": []})

    def unreachable(self):
        self.route.mock(side_effect=httpx.ConnectError("fake connection refused"))

    def report_error(self, message):
        self.answer({self.part: [], "sources": [], "error": message})

    def serve(self, app):
        """Pass requests on to a real specialist app, in process."""

        async def forward(request):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url=AGENT_URLS[self.service]) as client:
                response = await client.send(request)
                return httpx.Response(response.status_code, headers=response.headers, content=await response.aread())

        self.route.mock(side_effect=forward)

    @property
    def requests(self):
        return [json.loads(call.request.content) for call in self.route.calls]

    @property
    def headers(self):
        return [call.request.headers for call in self.route.calls]
