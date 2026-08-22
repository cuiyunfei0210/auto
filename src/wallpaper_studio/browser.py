from __future__ import annotations

import os
import sys
from pathlib import Path

# CQwall's fixed header is 1600px wide (`body { --width: 1600px }`) with Sign in
# on the far right. Playwright's default 1280x720 viewport leaves that link
# outside the window, so the click retries until the 45s timeout.
DESKTOP_VIEWPORT = {"width": 1920, "height": 1080}


def browser_context_options() -> dict:
    return {"viewport": dict(DESKTOP_VIEWPORT)}


async def click_even_if_offscreen(locator, timeout_ms: int = 8000) -> None:
    """Click a header/overlay control that Playwright may treat as off-screen."""
    try:
        await locator.scroll_into_view_if_needed(timeout=min(3000, timeout_ms))
    except Exception:
        pass
    try:
        await locator.click(timeout=min(5000, timeout_ms))
        return
    except Exception:
        pass
    try:
        await locator.click(force=True, timeout=min(5000, timeout_ms))
        return
    except Exception:
        pass
    await locator.evaluate("el => el.click()")


def configure_playwright_env() -> None:
    """Make frozen exes look for browsers next to the bundled Playwright driver."""
    if not getattr(sys, "frozen", False):
        return
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")
    meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    bundled = meipass / "playwright" / "driver" / "package" / ".local-browsers"
    if bundled.exists():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(bundled)


def chromium_launch_attempts(headless: bool, proxy: str | None) -> list[dict]:
    """Try the bundled Chromium first, then Windows Edge/Chrome if that binary is missing."""
    base: dict = {"headless": headless}
    if proxy:
        base["proxy"] = {"server": proxy}
    attempts = [dict(base)]
    if os.name == "nt":
        attempts.append({**base, "channel": "msedge"})
        attempts.append({**base, "channel": "chrome"})
    return attempts
