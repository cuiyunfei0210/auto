from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_root() -> Path:
    """Directory that owns data/, start.bat, and the Windows exe."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    repo = Path(__file__).resolve().parents[2]
    if (repo / "run.py").exists() or (repo / "pyproject.toml").exists():
        return repo
    return Path.cwd()


def web_dir() -> Path:
    if is_frozen():
        meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        bundled = meipass / "wallpaper_studio" / "web"
        if bundled.exists():
            return bundled
    return Path(__file__).resolve().parent / "web"
