"""The API key on the Host's POST /run (TP-SRS-110 to TP-SRS-112)."""

import hmac

from starlette.responses import JSONResponse

UNAUTHORIZED = {"detail": "A valid X-API-Key header is required."}


class ApiKeyMiddleware:
    """Rejects POST /run without a matching X-API-Key, before the body is read or validated."""

    def __init__(self, app, api_key, path="/run"):
        self.app = app
        self.expected = api_key.encode()
        self.path = path

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] == "POST" and scope["path"] == self.path:
            given = dict(scope["headers"]).get(b"x-api-key")
            # Constant-time comparison, so response timing reveals nothing about the key (TP-SRS-111).
            if given is None or not hmac.compare_digest(given, self.expected):
                await JSONResponse(UNAUTHORIZED, status_code=401)(scope, receive, send)
                return
        await self.app(scope, receive, send)
