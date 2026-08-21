from __future__ import annotations

import threading
from typing import Any

class JobStopped(RuntimeError):
    """Raised when the user clicks Stop and the rest of the job should be abandoned."""


_stop = threading.Event()
_clients: list[Any] = []
_lock = threading.Lock()


def clear_stop() -> None:
    _stop.clear()
    with _lock:
        _clients.clear()


def stop_requested() -> bool:
    return _stop.is_set()


def request_stop() -> None:
    _stop.set()
    abort_http()


def push_http(client: Any) -> None:
    with _lock:
        _clients.append(client)


def pop_http(client: Any) -> None:
    with _lock:
        try:
            _clients.remove(client)
        except ValueError:
            pass


def abort_http() -> None:
    with _lock:
        snapshot = list(_clients)
    for client in snapshot:
        try:
            client.close()
        except Exception:
            pass


def wait_or_stop(seconds: float, step: float = 0.2) -> None:
    """Sleep, but raise JobStopped as soon as stop is requested."""
    import time

    if seconds <= 0:
        if stop_requested():
            raise JobStopped("已手动停止")
        return
    end = time.time() + seconds
    while True:
        if stop_requested():
            raise JobStopped("已手动停止")
        remaining = end - time.time()
        if remaining <= 0:
            return
        time.sleep(min(step, remaining))
