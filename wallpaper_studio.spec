# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs

root = Path(SPECPATH).resolve()
web = root / "src" / "wallpaper_studio" / "web"
readme = root / "packaging" / "exe-readme.txt"


def _windows_runtime_binaries() -> list[tuple[str, str]]:
    """Ship python312.dll, VC runtime, and CPython stdlib extensions.

    Frozen Windows builds import multiprocessing before app code. That path
    loads socket.py, which needs _socket.pyd from Python's DLLs folder.
    PyInstaller sometimes omits those .pyd files; the exe then dies with
    pyi_rth_multiprocessing / No module named '_socket'.
    """
    if sys.platform != "win32":
        return []
    names = (
        "python312.dll",
        "python3.dll",
        "vcruntime140.dll",
        "vcruntime140_1.dll",
        "msvcp140.dll",
        "_socket.pyd",
        "select.pyd",
        "_ssl.pyd",
        "_hashlib.pyd",
        "_ctypes.pyd",
        "_multiprocessing.pyd",
        "_overlapped.pyd",
        "_asyncio.pyd",
        "_queue.pyd",
        "_bz2.pyd",
        "_lzma.pyd",
        "_decimal.pyd",
        "_uuid.pyd",
        "_zoneinfo.pyd",
        "_sqlite3.pyd",
        "_elementtree.pyd",
        "pyexpat.pyd",
        "unicodedata.pyd",
        "libffi-8.dll",
        "sqlite3.dll",
    )
    directories = [
        Path(sys.base_prefix),
        Path(sys.base_prefix) / "DLLs",
        Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32",
    ]
    found: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(src: Path) -> None:
        key = src.name.lower()
        if key in seen or not src.is_file():
            return
        seen.add(key)
        found.append((str(src), "."))

    for directory in directories:
        for name in names:
            add(directory / name)
        if directory.name.lower() == "dlls" and directory.is_dir():
            for src in directory.iterdir():
                lower = src.name.lower()
                if lower.endswith(".pyd") and not lower.startswith(("_tkinter", "tcl", "tk")):
                    add(src)
                elif lower.startswith(("libcrypto", "libssl", "libffi")) and lower.endswith(".dll"):
                    add(src)
    return found


datas = [(str(web), "wallpaper_studio/web")]
if readme.exists():
    datas.append((str(readme), "."))

datas += [
    (src, dest)
    for src, dest in collect_data_files("playwright")
    if ".local-browsers" not in Path(src).as_posix()
]
binaries = collect_dynamic_libs("playwright") + _windows_runtime_binaries()
hiddenimports = [
    "socket",
    "_socket",
    "select",
    "selectors",
    "ssl",
    "_ssl",
    "multiprocessing",
    "multiprocessing.connection",
    "multiprocessing.context",
    "multiprocessing.reduction",
    "multiprocessing.spawn",
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
    "wallpaper_studio.desktop",
    "webview",
    "bottle",
    "proxy_tools",
]
if sys.platform == "win32":
    hiddenimports += [
        "clr",
        "clr_loader",
        "pythonnet",
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
    ]


def _collect_pkg(name: str) -> None:
    try:
        extra_datas, extra_binaries, extra_hidden = collect_all(name)
    except Exception:
        return
    datas.extend(extra_datas)
    binaries.extend(extra_binaries)
    hiddenimports.extend(extra_hidden)


for _pkg in ("webview", "bottle", "proxy_tools"):
    _collect_pkg(_pkg)
if sys.platform == "win32":
    for _pkg in ("pythonnet", "clr_loader"):
        _collect_pkg(_pkg)

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
    hiddenimports=hiddenimports,
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
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="WallpaperStudio",
)
