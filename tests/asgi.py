"""Call an agent's app in process, without a socket (TDD plan §2.1)."""

import asyncio

import httpx


class AppClient:
    """A synchronous client for an ASGI app, built on httpx.ASGITransport."""

    def __init__(self, app):
        self.app = app

    def request(self, method, path, **kwargs):
        return asyncio.run(self._request(method, path, **kwargs))

    async def _request(self, method, path, **kwargs):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://agent") as client:
            return await client.request(method, path, **kwargs)

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)
