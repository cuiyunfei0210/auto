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


def test_config_clears_image_size_limits(studio_home):
    reset_demo_sessions()
    client = TestClient(create_app())
    payload = client.get("/api/state").json()["config"]
    payload["site"]["min_width"] = 1920
    payload["site"]["min_height"] = 1080
    saved = client.post("/api/config", json=payload)
    assert saved.status_code == 200
    site = saved.json()["config"]["site"]
    assert site["min_width"] == 0
    assert site["min_height"] == 0


def test_start_rejects_shared_proxy(studio_home):
    reset_demo_sessions()
    client = TestClient(create_app())
    payload = client.get("/api/state").json()["config"]
    payload["accounts"] = [
        {"username": "demo1", "password": "123123", "upload_count": 1, "interval_seconds": 0},
        {"username": "demo2", "password": "123123", "upload_count": 1, "interval_seconds": 0},
    ]
    payload["network"] = {
        "proxy_enabled": True,
        "unique_ip_per_account": True,
        "rotate_every_accounts": 1,
        "proxies": ["http://10.0.0.1:8080"],
    }
    assert client.post("/api/config", json=payload).status_code == 200
    state = client.get("/api/state").json()
    assert state["proxy_error"]
    started = client.post("/api/start")
    assert started.status_code == 400
    assert "独立出口" in started.json()["error"]


def test_empty_accounts_are_restored_to_default(studio_home):
    reset_demo_sessions()
    client = TestClient(create_app())
    payload = client.get("/api/state").json()["config"]
    payload["accounts"] = []
    assert client.post("/api/config", json=payload).status_code == 200
    state = client.get("/api/state").json()["config"]
    assert state["accounts"][0]["username"] == "ari-ihcot@linshi-mail.com"


def test_default_state_includes_cqwall_and_xbhuiz(studio_home):
    reset_demo_sessions()
    client = TestClient(create_app())
    state = client.get("/api/state").json()["config"]
    assert state["accounts"][0]["username"] == "ari-ihcot@linshi-mail.com"
    assert "xbhuiz.com" in state["api"]["base_url"]
    assert state["api"]["username"] == "596003517@qq.com"


def test_state_includes_archive_warning_field(studio_home):
    reset_demo_sessions()
    client = TestClient(create_app())
    state = client.get("/api/state").json()
    assert "archive_warning" in state
    assert state["archive_warning"] is None
