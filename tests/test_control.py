import time

import httpx
import pytest

from wallpaper_studio.control import (
    JobStopped,
    abort_http,
    clear_stop,
    pop_http,
    push_http,
    request_stop,
    stop_requested,
    wait_or_stop,
)


def test_wait_or_stop_raises_when_stop_requested():
    clear_stop()
    request_stop()
    with pytest.raises(JobStopped):
        wait_or_stop(1)
    clear_stop()
    start = time.time()
    wait_or_stop(0.05)
    assert time.time() - start < 0.5
    assert stop_requested() is False


def test_abort_http_closes_tracked_client():
    clear_stop()
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"ok": True}))
    client = httpx.Client(transport=transport)
    push_http(client)
    abort_http()
    with pytest.raises(Exception):
        client.get("https://example.test/")
    pop_http(client)
    client.close()
    clear_stop()
