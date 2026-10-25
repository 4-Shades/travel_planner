"""Request IDs in every log line (TP-SRS-005)."""

import contextvars
import logging
import re
import uuid

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"

# Accepted from callers as-is; anything else is replaced so it cannot forge log lines.
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

_current = contextvars.ContextVar("request_id", default="-")


def current_request_id():
    return _current.get()


def _install_record_factory():
    base_factory = logging.getLogRecordFactory()

    def factory(*args, **kwargs):
        record = base_factory(*args, **kwargs)
        record.request_id = _current.get()
        return record

    logging.setLogRecordFactory(factory)


_install_record_factory()


class RequestIdMiddleware:
    """Reads X-Request-ID, or makes one up, and logs the start and end of each request."""

    def __init__(self, app, logger):
        self.app = app
        self.logger = logger

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        given = dict(scope["headers"]).get(b"x-request-id", b"").decode("latin-1")
        token = _current.set(given if _SAFE_ID.match(given) else uuid.uuid4().hex)
        status = 500

        async def send_with_status(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        self.logger.info("%s %s started", scope["method"], scope["path"])
        try:
            await self.app(scope, receive, send_with_status)
        finally:
            self.logger.info("%s %s finished with status %s", scope["method"], scope["path"], status)
            _current.reset(token)
