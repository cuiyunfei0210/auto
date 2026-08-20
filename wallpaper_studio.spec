# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

root = Path(SPECPATH).resolve()
web = root / "src" / "wallpaper_studio" / "web"
readme = root / "packaging" / "exe-readme.txt"

datas = [(str(web), "wallpaper_studio/web")]
if readme.exists():
    datas.append((str(readme), "."))

datas += [
    (src, dest)
    for src, dest in collect_data_files("playwright")
    if ".local-browsers" not in Path(src).as_posix()
]
binaries = collect_dynamic_libs("playwright")

try:
    import playwright
except ImportError as exc:  # pragma: no cover - build-time check
    raise SystemExit("Playwright is not installed in the build environment.") from exc

# macOS PyInstaller codesign fails on Google Chrome for Testing.app.
# Windows/Linux keep the bundled Chromium; macOS uses the system Chrome at runtime.
if sys.platform != "darwin":
    local_browsers = Path(playwright.__file__).resolve().parent / "driver" / "package" / ".local-browsers"
    if not local_browsers.exists() or not any(local_browsers.iterdir()):
        raise SystemExit(
            "Playwright browsers are missing. Set PLAYWRIGHT_BROWSERS_PATH=0 and run: "
            "python -m playwright install chromium"
        )
    datas.append((str(local_browsers), "playwright/driver/package/.local-browsers"))

a = Analysis(
    [str(root / "run.py")],
    pathex=[str(root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.lifespan.on",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "multipart",
        "starlette",
        "fastapi",
        "playwright",
        "playwright.sync_api",
        "playwright.async_api",
        "wallpaper_studio.browser",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WallpaperStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="WallpaperStudio",
)
