from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from wallpaper_studio.demo_site import reset_demo_sessions
from wallpaper_studio.server import create_app


def png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (16, 16), (20, 80, 160)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_demo_login_and_upload(studio_home):
    reset_demo_sessions()
    client = TestClient(create_app())
    denied = client.post("/demo/login", data={"username": "demo1", "password": "wrong"})
    assert denied.status_code == 401

    login = client.post("/demo/login", data={"username": "demo1", "password": "123123"}, follow_redirects=False)
    assert login.status_code == 303

    uploaded = client.post(
        "/demo/upload",
        data={"title": "蓝天壁纸", "category": "风景"},
        files={"file": ("sky.png", png_bytes(), "image/png")},
        follow_redirects=True,
    )
    assert uploaded.status_code == 200
    assert "上传成功" in uploaded.text

    listing = client.get("/demo/api/uploads/demo1")
    assert listing.json()["items"][0]["title"].startswith("蓝天壁纸")
