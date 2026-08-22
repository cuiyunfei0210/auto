from http.server import BaseHTTPRequestHandler, HTTPServer
import sys
import threading
import types

import pytest

from wallpaper_studio.desktop import (
    DesktopWindowError,
    close_native_windows,
    open_native_window,
    should_open_native_window,
    wait_until_up,
)


def test_native_window_is_the_default():
    assert should_open_native_window(web=False, no_browser=False) is True
    assert should_open_native_window(web=True, no_browser=False) is False
    assert should_open_native_window(web=False, no_browser=True) is False


def test_wait_until_up_requires_health():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"ok": true}')

        def log_message(self, *_args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        wait_until_up(f"http://127.0.0.1:{port}", timeout=2, pause=0.05)
        with pytest.raises(DesktopWindowError, match="超时"):
            wait_until_up("http://127.0.0.1:1", timeout=0.3, pause=0.05)
    finally:
        server.shutdown()


def test_open_native_window_loads_local_ui(monkeypatch):
    created: dict = {}

    class FakeWindow:
        def __init__(self):
            self.events = type("Events", (), {"closed": 0})()

        def destroy(self):
            created["destroyed"] = True

    def fake_create_window(title, url, **kwargs):
        created["title"] = title
        created["url"] = url
        return FakeWindow()

    def fake_start(**kwargs):
        created["started"] = kwargs

    fake = types.ModuleType("webview")
    fake.create_window = fake_create_window
    fake.start = fake_start
    fake.windows = []
    monkeypatch.setitem(sys.modules, "webview", fake)
    monkeypatch.setattr("wallpaper_studio.desktop.wait_until_up", lambda url: None)

    open_native_window("http://127.0.0.1:8765")
    assert created["title"] == "壁纸工坊"
    assert created["url"] == "http://127.0.0.1:8765"
    assert "started" in created


def test_close_native_windows_destroys_open_windows(monkeypatch):
    class FakeWindow:
        def __init__(self):
            self.destroyed = False

        def destroy(self):
            self.destroyed = True

    window = FakeWindow()
    fake = types.ModuleType("webview")
    fake.windows = [window]
    monkeypatch.setitem(sys.modules, "webview", fake)
    close_native_windows()
    assert window.destroyed is True
