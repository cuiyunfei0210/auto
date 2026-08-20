from __future__ import annotations

import socket
import threading
import time

import pytest
import uvicorn
from fastapi.testclient import TestClient

from wallpaper_studio.demo_site import reset_demo_sessions
from wallpaper_studio.jobs import run_job
from wallpaper_studio.models import Account, AppConfig, PathSettings, SiteProfile
from wallpaper_studio.server import create_app
from wallpaper_studio.storage import save_config, source_dir, data_dir
from tests.helpers import make_png


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.fixture
def live_server(studio_home):
    reset_demo_sessions()
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.05)
    if not server.started:
        pytest.skip("demo server failed to start")
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=3)


async def test_playwright_uploads_then_switches_account(studio_home, live_server):
    pytest.importorskip("playwright")
    try:
        from playwright.async_api import async_playwright
    except Exception:
        pytest.skip("playwright is not available")

    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch(headless=True)
        except Exception:
            pytest.skip("chromium is not installed; run playwright install chromium")
        await browser.close()

    config = AppConfig(
        mode="upload_only",
        paths=PathSettings(source_dir=str(studio_home / "source"), output_dir=str(studio_home / "output")),
        site=SiteProfile(
            login_url=f"{live_server}/demo/login",
            upload_url=f"{live_server}/demo/upload",
            headless=True,
        ),
        accounts=[
            Account(username="demo1", password="123123", upload_count=1, interval_seconds=0),
            Account(username="demo2", password="123123", upload_count=1, interval_seconds=0),
        ],
    )
    save_config(config)
    make_png(source_dir(config) / "one.png", (210, 80, 40))
    make_png(source_dir(config) / "two.png", (40, 120, 200))

    result = await run_job(config)
    assert result["uploaded"] == 2
    assert result["accounts_used"] == 2

    client = TestClient(create_app())
    demo1 = client.get("/demo/api/uploads/demo1").json()["items"]
    demo2 = client.get("/demo/api/uploads/demo2").json()["items"]
    assert len(demo1) == 1
    assert len(demo2) == 1
    assert (data_dir() / "demo_uploads" / "demo1").exists()
    assert (data_dir() / "demo_uploads" / "demo2").exists()
