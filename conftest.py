"""Settings shared by every pytest run in the repository, for tests/ and features/."""

import socket
import sys

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
