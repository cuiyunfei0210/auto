import os

from wallpaper_studio.browser import (
    DESKTOP_VIEWPORT,
    browser_context_options,
    chromium_launch_attempts,
    click_even_if_offscreen,
    configure_playwright_env,
)


def test_windows_launch_prefers_system_edge(monkeypatch):
    monkeypatch.setattr("wallpaper_studio.browser.os.name", "nt")
    attempts = chromium_launch_attempts(True, "http://127.0.0.1:8080")
    assert attempts[0] == {"headless": True, "proxy": {"server": "http://127.0.0.1:8080"}, "channel": "msedge"}
    assert attempts[1]["channel"] == "chrome"
    assert "channel" not in attempts[2]


def test_non_windows_launch_uses_playwright_chromium(monkeypatch):
    monkeypatch.setattr("wallpaper_studio.browser.os.name", "posix")
    assert chromium_launch_attempts(True, None) == [{"headless": True}]


def test_frozen_env_points_at_bundled_browsers(tmp_path, monkeypatch):
    bundled = tmp_path / "pw-browsers"
    bundled.mkdir()
    (bundled / "chromium-1").mkdir()
    monkeypatch.setattr("wallpaper_studio.browser.sys.frozen", True, raising=False)
    monkeypatch.setattr("wallpaper_studio.browser.sys.executable", str(tmp_path / "WallpaperStudio.exe"), raising=False)
    monkeypatch.setattr("wallpaper_studio.browser.sys._MEIPASS", str(tmp_path), raising=False)
    monkeypatch.delitem(os.environ, "PLAYWRIGHT_BROWSERS_PATH", raising=False)
    configure_playwright_env()
    assert os.environ["PLAYWRIGHT_BROWSERS_PATH"] == str(bundled)


def test_frozen_env_falls_back_to_playwright_dotfolder(tmp_path, monkeypatch):
    bundled = tmp_path / "playwright" / "driver" / "package" / ".local-browsers"
    bundled.mkdir(parents=True)
    (bundled / "chromium-1").mkdir()
    monkeypatch.setattr("wallpaper_studio.browser.sys.frozen", True, raising=False)
    monkeypatch.setattr("wallpaper_studio.browser.sys.executable", str(tmp_path / "WallpaperStudio.exe"), raising=False)
    monkeypatch.setattr("wallpaper_studio.browser.sys._MEIPASS", str(tmp_path), raising=False)
    monkeypatch.delitem(os.environ, "PLAYWRIGHT_BROWSERS_PATH", raising=False)
    configure_playwright_env()
    assert os.environ["PLAYWRIGHT_BROWSERS_PATH"] == str(bundled)


def test_desktop_viewport_fits_cqwall_header():
    assert DESKTOP_VIEWPORT["width"] >= 1600
    assert browser_context_options()["viewport"]["width"] >= 1600


async def test_click_falls_back_to_force_when_outside_viewport():
    class Locator:
        def __init__(self) -> None:
            self.calls: list[tuple] = []

        async def scroll_into_view_if_needed(self, timeout=None):
            self.calls.append(("scroll", timeout))

        async def click(self, timeout=None, force=False):
            self.calls.append(("click", force, timeout))
            if not force:
                raise RuntimeError("element is outside of the viewport")

        async def evaluate(self, script):
            self.calls.append(("evaluate", script))

    locator = Locator()
    await click_even_if_offscreen(locator, timeout_ms=45000)
    assert ("click", False, 5000) in locator.calls
    assert ("click", True, 5000) in locator.calls
    assert not any(call[0] == "evaluate" for call in locator.calls)
