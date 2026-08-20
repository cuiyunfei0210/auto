from fastapi.testclient import TestClient

from wallpaper_studio.demo_site import reset_demo_sessions
from wallpaper_studio.server import create_app


def test_home_and_config_roundtrip(studio_home):
    reset_demo_sessions()
    client = TestClient(create_app())
    home = client.get("/")
    assert home.status_code == 200
    assert "壁纸工坊" in home.text

    state = client.get("/api/state")
    assert state.status_code == 200
    payload = state.json()["config"]
    payload["mode"] = "upload_only"
    payload["accounts"] = [
        {"username": "demo1", "password": "123123", "upload_count": 2, "interval_seconds": 1}
    ]
    saved = client.post("/api/config", json=payload)
    assert saved.status_code == 200
    assert saved.json()["config"]["accounts"][0]["username"] == "demo1"
