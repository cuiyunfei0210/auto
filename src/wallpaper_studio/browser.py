from __future__ import annotations

import os
import sys
from pathlib import Path


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
