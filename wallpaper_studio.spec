# -*- mode: python ; coding: utf-8 -*-
import importlib.util
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs

root = Path(SPECPATH).resolve()
web = root / "src" / "wallpaper_studio" / "web"
readme = root / "packaging" / "exe-readme.txt"


def _load_windows_runtime():
    path = root / "packaging" / "windows_runtime.py"
    spec = importlib.util.spec_from_file_location("ws_windows_runtime", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_windows_runtime = _load_windows_runtime()


datas = [(str(web), "wallpaper_studio/web")]
if readme.exists():
    datas.append((str(readme), "."))

datas += [
    (src, dest)
    for src, dest in collect_data_files("playwright")
    if ".local-browsers" not in Path(src).as_posix()
]
binaries = [
    (src, dest)
    for src, dest in collect_dynamic_libs("playwright")
    if ".local-browsers" not in Path(src).as_posix()
] + _windows_runtime.runtime_binary_tuples()
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
    import playwright  # noqa: F401 — freeze-time check; Chromium itself is not shipped
except ImportError as exc:  # pragma: no cover - build-time check
    raise SystemExit("Playwright is not installed in the build environment.") from exc

# Do not ship Playwright's Chromium. It is ~600MB and makes client-Windows ~700MB.
# Frozen Windows launches the installed Edge or Chrome instead.

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
if sys.platform == "win32":
    # Analysis may strip UCRT/api-ms-win-crt as "system DLLs". Put them back.
    have = {str(item[0]).replace("\\", "/").split("/")[-1].lower() for item in a.binaries}
    for src, _dest in _windows_runtime.runtime_binary_tuples():
        name = Path(src).name
        if name.lower() in have:
            continue
        a.binaries.append((name, src, "BINARY"))
        have.add(name.lower())
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
if sys.platform == "win32":
    _windows_runtime.copy_runtime_into(Path(DISTPATH) / "WallpaperStudio")
