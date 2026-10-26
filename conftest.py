"""Fixtures shared by every pytest run in the repository, for tests/ and features/."""

import socket
import sys

import pytest

# pytest-socket (enabled in pyproject.toml) blocks every new socket so that no test can
# reach a real service (TP-SRS-187). On Windows, asyncio event loops build their internal
# wake-up channel with socket.socketpair(), which is implemented with ordinary sockets
# connected over the loopback interface, so it is blocked too. Captured here, before
# pytest-socket patches socket.socket, the real class is used for socketpair() only.
if sys.platform == "win32":
    _real_socket = socket.socket
    _real_socketpair = socket.socketpair

    def _socketpair_for_event_loops(*args, **kwargs):
        guarded_socket = socket.socket
        socket.socket = _real_socket
        try:
            return _real_socketpair(*args, **kwargs)
        finally:
            socket.socket = guarded_socket

    socket.socketpair = _socketpair_for_event_loops


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch):
    """Start every test from default settings, whatever the developer's shell has set."""
    from shared.config import ENV_VARS

    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def settings(monkeypatch):
    """Factory that sets environment variables and builds fresh settings: settings(RAG_TOP_K="3")."""
    from shared.config import Settings

    def build(**env):
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        return Settings.from_env()

    return build


@pytest.fixture
def agent_app(settings):
    """Factory that builds an agent's app from environment variables: agent_app("host", HOST_API_KEY="k").

    metrics, if given, replaces the metrics the app would set up from its settings.
    """
    from agents.host.app import create_host_app
    from agents.specialist import create_specialist_app

    def build(service, metrics=None, **env):
        config = settings(**env)
        if service == "host":
            return create_host_app(config, metrics=metrics)
        return create_specialist_app(service, config, metrics=metrics)

    return build
