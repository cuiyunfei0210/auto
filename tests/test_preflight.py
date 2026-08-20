from wallpaper_studio.models import Account, ApiSettings, AppConfig, PathSettings
from wallpaper_studio.preflight import format_start_problems, start_problems
from tests.helpers import make_png


def test_start_problems_reports_missing_source_images(studio_home):
    config = AppConfig(
        mode="upload_only",
        accounts=[Account(username="demo1", password="123123")],
        paths=PathSettings(source_dir=str(studio_home / "source")),
    )
    problems = start_problems(config)
    assert any("没有图片" in item for item in problems)
    text = format_start_problems(problems)
    assert "没有图片" in text


def test_start_problems_reports_remix_without_credentials(studio_home):
    make_png(studio_home / "source" / "one.png")
    config = AppConfig(
        mode="remix_then_upload",
        api=ApiSettings(base_url="https://xmapi.site", api_key="", username="", password=""),
        accounts=[Account(username="demo1", password="123123")],
        paths=PathSettings(source_dir=str(studio_home / "source")),
    )
    problems = start_problems(config)
    assert any("API Key" in item for item in problems)


def test_start_rejects_empty_source_folder(studio_home):
    from fastapi.testclient import TestClient

    from wallpaper_studio.demo_site import reset_demo_sessions
    from wallpaper_studio.server import create_app

    reset_demo_sessions()
    client = TestClient(create_app())
    payload = client.get("/api/state").json()["config"]
    payload["mode"] = "upload_only"
    payload["paths"]["source_dir"] = str(studio_home / "source")
    payload["accounts"] = [{"username": "demo1", "password": "123123", "upload_count": 1, "interval_seconds": 0}]
    assert client.post("/api/config", json=payload).status_code == 200
    started = client.post("/api/start")
    assert started.status_code == 400
    body = started.json()
    assert body["ok"] is False
    assert "没有图片" in body["error"]
    assert body["problems"]
