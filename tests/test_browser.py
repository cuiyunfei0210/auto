import os

from wallpaper_studio.browser import chromium_launch_attempts, configure_playwright_env


def test_windows_launch_falls_back_to_edge_and_chrome(monkeypatch):
    monkeypatch.setattr("wallpaper_studio.browser.os.name", "nt")
    attempts = chromium_launch_attempts(True, "http://127.0.0.1:8080")
    assert attempts[0] == {"headless": True, "proxy": {"server": "http://127.0.0.1:8080"}}
    assert attempts[1]["channel"] == "msedge"
    assert attempts[2]["channel"] == "chrome"


def test_frozen_env_points_at_bundled_browsers(tmp_path, monkeypatch):
    bundled = tmp_path / "playwright" / "driver" / "package" / ".local-browsers"
    bundled.mkdir(parents=True)
    monkeypatch.setattr("wallpaper_studio.browser.sys.frozen", True, raising=False)
    monkeypatch.setattr("wallpaper_studio.browser.sys.executable", str(tmp_path / "WallpaperStudio.exe"), raising=False)
    monkeypatch.setattr("wallpaper_studio.browser.sys._MEIPASS", str(tmp_path), raising=False)
    monkeypatch.delitem(os.environ, "PLAYWRIGHT_BROWSERS_PATH", raising=False)
    configure_playwright_env()
    assert os.environ["PLAYWRIGHT_BROWSERS_PATH"] == str(bundled)
