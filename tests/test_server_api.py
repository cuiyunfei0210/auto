from fastapi.testclient import TestClient

from wallpaper_studio.demo_site import reset_demo_sessions
from wallpaper_studio.server import create_app


def test_home_and_config_roundtrip(studio_home):
    reset_demo_sessions()
    client = TestClient(create_app())
    home = client.get("/")
    assert home.status_code == 200
    assert "壁纸工坊" in home.text
    js = client.get("/static/studio.js")
    assert js.status_code == 200
    assert "function renderLogs" in js.text
    assert "function notify" in js.text
    assert "charset=utf-8" in (js.headers.get("content-type") or "").lower()
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True

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


def test_blank_remix_prompt_is_saved_as_default(studio_home):
    reset_demo_sessions()
    client = TestClient(create_app())
    payload = client.get("/api/state").json()["config"]
    payload["api"]["remix_prompt"] = ""
    saved = client.post("/api/config", json=payload)
    assert saved.status_code == 200
    prompt = saved.json()["config"]["api"]["remix_prompt"]
    assert "禁止原样" in prompt
    assert client.get("/api/state").json()["config"]["api"]["remix_prompt"] == prompt


def test_default_state_includes_cqwall_and_xbhuiz(studio_home):
    reset_demo_sessions()
    client = TestClient(create_app())
    state = client.get("/api/state").json()["config"]
    assert state["accounts"][0]["username"] == "ari-ihcot@linshi-mail.com"
    assert "xmapi.site" in state["api"]["base_url"]
    assert state["api"]["api_key"].startswith("sk-")


def test_state_includes_archive_warning_field(studio_home):
    reset_demo_sessions()
    client = TestClient(create_app())
    state = client.get("/api/state").json()
    assert "archive_warning" in state
    assert state["archive_warning"] is None
    assert "source_note" in state
    assert "没有图片" in state["source_note"]
    assert state["remix_pending"] == 0


def test_start_returns_409_when_a_job_is_already_running(studio_home):
    from wallpaper_studio.server import state as studio_state

    reset_demo_sessions()
    client = TestClient(create_app())
    studio_state.running = True
    try:
        started = client.post("/api/start")
        assert started.status_code == 409
        assert "正在运行" in started.json()["error"]
    finally:
        studio_state.running = False


def test_log_note_keeps_failure_after_progress():
    from wallpaper_studio.server import StudioState

    studio = StudioState()
    studio.note("正在准备待上传图片…")
    studio.note("正在二创 wall.png …")
    studio.note("任务失败：上游暂时不可用")
    assert studio.logs[0].startswith("正在准备")
    assert studio.logs[1].startswith("正在二创")
    assert studio.logs[-1].startswith("任务失败")


def test_state_counts_nested_source_images(studio_home):
    from tests.helpers import make_png

    reset_demo_sessions()
    nested = studio_home / "source" / "batch"
    make_png(nested / "one.png")
    client = TestClient(create_app())
    state = client.get("/api/state").json()
    assert state["source_count"] == 1
    assert state["source_note"] == ""
    assert "one.png" in state["source_samples"]
    assert state["remix_pending"] == 0


def test_state_remix_pending_matches_source_images(studio_home):
    from tests.helpers import make_png
    from wallpaper_studio.models import AppConfig, PathSettings
    from wallpaper_studio.storage import save_config

    make_png(studio_home / "source" / "a.png")
    make_png(studio_home / "source" / "b.png", (1, 2, 3))
    save_config(AppConfig(mode="remix_then_upload", paths=PathSettings(source_dir=str(studio_home / "source"))))
    reset_demo_sessions()
    client = TestClient(create_app())
    state = client.get("/api/state").json()
    assert state["source_count"] == 2
    assert state["remix_pending"] == 2
    assert state["remix_total"] == 2


def test_state_ignores_other_pc_source_path(studio_home, monkeypatch):
    from tests.helpers import make_png
    from wallpaper_studio.models import AppConfig, PathSettings
    from wallpaper_studio.storage import save_config

    monkeypatch.setenv("USERNAME", "Bob")
    monkeypatch.setenv("USER", "Bob")
    make_png(studio_home / "source" / "local.png")
    save_config(
        AppConfig(
            paths=PathSettings(
                source_dir=r"C:\Users\Administrator\Desktop\WallpaperStudio\data\source",
            )
        )
    )
    reset_demo_sessions()
    client = TestClient(create_app())
    response = client.get("/api/state")
    assert response.status_code == 200
    body = response.json()
    assert body["source_count"] == 1
    assert "local.png" in body["source_samples"]
    assert "Administrator" not in body["source_dir"]


def test_shutdown_endpoint_stops_without_killing_tests(studio_home):
    reset_demo_sessions()
    client = TestClient(create_app())
    stopped = client.post("/api/shutdown")
    assert stopped.status_code == 200
    assert stopped.json()["ok"] is True


def test_state_error_payload_is_json(studio_home, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("scan exploded")

    monkeypatch.setattr("wallpaper_studio.server.list_images", boom)
    reset_demo_sessions()
    client = TestClient(create_app())
    response = client.get("/api/state")
    assert response.status_code == 200
    body = response.json()
    assert body["source_count"] == 0
    assert "scan exploded" in (body.get("source_note") or "")
