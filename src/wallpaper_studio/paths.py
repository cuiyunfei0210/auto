from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    if getattr(sys, "frozen", False):
        return True
    if os.environ.get("WALLPAPER_STUDIO_PACKAGED") == "1":
        return True
    executable = Path(sys.executable).resolve()
    parent = executable.parent
    if executable.name.lower() in {"python.exe", "pythonw.exe"} and (parent / "python312.dll").is_file() and (parent / "run.py").is_file():
        return True
    return False


def is_archive_temp_path(path: Path | None = None) -> bool:
    """True if the program is running from a zip/rar 'open without extracting' temp folder."""
    text = str(path or app_root()).replace("/", "\\").lower()
    needles = (
        "rar$ex",
        "rartemp",
        r"\temp\7zo",
        r"\temp\wz",
        "\\inetcache\\",
        "\\content.outlook\\",
        "\\temporary internet files\\",
    )
    return any(needle in text for needle in needles)


def archive_temp_warning(path: Path | None = None) -> str | None:
    if not is_frozen():
        return None
    if not is_archive_temp_path(path):
        return None
    return (
        "程序正在压缩包临时目录里运行（没有先解压）。"
        "请先把整个 WallpaperStudio 文件夹解压到桌面或 D 盘，再双击里面的 WallpaperStudio.exe。"
        "不要直接双击压缩包里的程序。"
    )


def app_root() -> Path:
    """Directory that owns data/, start.bat, and the Windows exe."""
    if os.environ.get("WALLPAPER_STUDIO_ROOT"):
        return Path(os.environ["WALLPAPER_STUDIO_ROOT"]).resolve()
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
