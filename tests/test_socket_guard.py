"""The socket guard that keeps the suite off the network (TP-SRS-187)."""

import asyncio
import socket

import pytest
from pytest_socket import SocketBlockedError

pytestmark = pytest.mark.filterwarnings("ignore:A test tried to use socket")


def test_remote_connection_is_blocked():
    with pytest.raises(SocketBlockedError):
        socket.create_connection(("example.com", 443), timeout=1)


def test_loopback_connection_is_blocked():
    # A local Ollama listens on 127.0.0.1, so loopback must be blocked as well.
    with pytest.raises(SocketBlockedError):
        socket.create_connection(("127.0.0.1", 11434), timeout=1)


@pytest.mark.asyncio
async def test_event_loop_still_runs():
    await asyncio.sleep(0)
