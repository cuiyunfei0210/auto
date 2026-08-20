from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from wallpaper_studio.instance_lock import (
    InstanceLock,
    InstanceLockError,
    already_running_message,
    ui_is_reachable,
    wait_and_open_ui,
)


def test_second_instance_is_rejected(studio_home):
    first = InstanceLock()
    first.acquire()
    second = InstanceLock()
    try:
        try:
            second.acquire()
            raise AssertionError("second instance should not start")
        except InstanceLockError as exc:
            assert "只能打开一次" in str(exc)
    finally:
        first.release()

    third = InstanceLock()
    third.acquire()
    third.release()


def test_already_running_message_points_at_existing_ui():
    text = already_running_message("http://127.0.0.1:8765")
    assert "只能打开一次" in text
    assert "http://127.0.0.1:8765" in text
    assert "任务管理器" in text


def test_ui_is_reachable_requires_health_endpoint():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.endswith("/api/health"):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"ok": true}')
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *_args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert ui_is_reachable(f"http://127.0.0.1:{port}")
        assert not ui_is_reachable("http://127.0.0.1:1")
    finally:
        server.shutdown()


def test_wait_and_open_ui_opens_after_health(monkeypatch):
    opened: list[str] = []
    monkeypatch.setattr("wallpaper_studio.instance_lock.open_ui", opened.append)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"ok": true}')

        def log_message(self, *_args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        wait_and_open_ui(url, retries=8, delay=0.05)
        assert opened == [url]
    finally:
        server.shutdown()


def test_live_ui_prevents_stale_takeover(studio_home):
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
    first = InstanceLock()
    first.acquire()
    try:
        second = InstanceLock()
        try:
            second.take_over_stale(f"http://127.0.0.1:{port}", grace_seconds=0)
            raise AssertionError("live UI should not be taken over")
        except InstanceLockError as exc:
            assert "只能打开一次" in str(exc)
    finally:
        first.release()
        server.shutdown()


def test_stale_lock_is_taken_over(studio_home):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    env = os.environ.copy()
    env["WALLPAPER_STUDIO_HOME"] = str(studio_home)
    env["WALLPAPER_STUDIO_LOCK_PORT"] = str(port)
    src = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")

    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "from wallpaper_studio.instance_lock import InstanceLock; import time; "
            "lock = InstanceLock(); lock.acquire(); time.sleep(30)",
        ],
        env=env,
    )
    lock_file = studio_home / "instance.lock"
    try:
        for _ in range(80):
            if lock_file.exists() and proc.poll() is None:
                break
            time.sleep(0.05)
        else:
            raise AssertionError("holder did not start")

        second = InstanceLock(port=port)
        second.take_over_stale("http://127.0.0.1:1", grace_seconds=0)
        for _ in range(40):
            if proc.poll() is not None:
                break
            time.sleep(0.05)
        assert proc.poll() is not None
        second.release()
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
