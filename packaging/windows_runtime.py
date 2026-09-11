"""Copy CPython + Visual C++/UCRT DLLs into a frozen Windows onedir build.

PyInstaller loads ``_internal\\python312.dll`` before any app code. If that DLL
(or vcruntime140 / Universal CRT) is missing, Windows shows:

    Failed to load Python DLL ... python312.dll
    LoadLibrary: 找不到指定的模块。

GitHub's full Windows image has those libraries in System32, so CI smoke tests
pass. Many Chinese “精简” Windows installs do not, so the same exe dies on the
user's desktop. Copying the redistributable DLLs next to the exe and into
``_internal`` makes LoadLibrary self-contained.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

RUNTIME_DLL_NAMES = (
    "python312.dll",
    "python3.dll",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
    "vcruntime140_threads.dll",
    "msvcp140.dll",
    "msvcp140_1.dll",
    "msvcp140_2.dll",
    "msvcp140_atomic_wait.dll",
    "msvcp140_codecvt_ids.dll",
    "concrt140.dll",
    "vccorlib140.dll",
    "ucrtbase.dll",
)

STDLIB_PYD_NAMES = (
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
)

MIN_PYTHON_DLL_BYTES = 1_000_000


def search_directories() -> list[Path]:
    directories: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        key = str(path).lower()
        if key in seen:
            return
        seen.add(key)
        directories.append(path)

    for prefix in (sys.base_prefix, sys.exec_prefix, sys.prefix):
        root = Path(prefix)
        add(root)
        add(root / "DLLs")
        add(root / "Library" / "bin")
    windir = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    add(windir / "System32")
    return directories


def iter_runtime_files() -> list[Path]:
    if sys.platform != "win32":
        return []
    found: dict[str, Path] = {}

    def add(src: Path) -> None:
        if src.is_file():
            found.setdefault(src.name.lower(), src)

    for directory in search_directories():
        if not directory.is_dir():
            continue
        for name in RUNTIME_DLL_NAMES + STDLIB_PYD_NAMES:
            add(directory / name)
        lower_name = directory.name.lower()
        try:
            entries = list(directory.iterdir())
        except OSError:
            continue
        for src in entries:
            lower = src.name.lower()
            if lower.startswith("api-ms-win-crt-") and lower.endswith(".dll"):
                add(src)
            elif lower.startswith(("libcrypto", "libssl", "libffi")) and lower.endswith(".dll"):
                add(src)
            elif lower_name == "dlls" and lower.endswith(".pyd") and not lower.startswith(("_tkinter", "tcl", "tk")):
                add(src)
            elif lower in ("libffi-8.dll", "sqlite3.dll"):
                add(src)
    return list(found.values())


def runtime_binary_tuples() -> list[tuple[str, str]]:
    """PyInstaller Analysis binaries: ``(src, dest_dir)``."""
    return [(str(path), ".") for path in iter_runtime_files()]


def copy_crt_dlls(app_dir: Path) -> list[Path]:
    """Copy VC++/UCRT DLLs into *app_dir* without replacing python312.dll."""
    app_dir = Path(app_dir)
    app_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for src in iter_runtime_files():
        if src.suffix.lower() != ".dll":
            continue
        lower = src.name.lower()
        if lower.startswith("python"):
            continue
        if not (
            lower.startswith(("vcruntime", "msvcp", "concrt", "vccorlib", "ucrtbase", "api-ms-win-crt-"))
            or lower.startswith("api-ms-win-crt-")
        ):
            continue
        dest = app_dir / src.name
        try:
            if dest.exists() and dest.stat().st_size >= max(1, src.stat().st_size):
                continue
            shutil.copy2(src, dest)
            copied.append(dest)
        except OSError:
            continue
    return copied


def copy_runtime_into(app_dir: Path) -> list[Path]:
    """Copy runtime files into ``_internal`` and VC/Python DLLs next to the exe."""
    app_dir = Path(app_dir)
    internal = app_dir / "_internal"
    internal.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for src in iter_runtime_files():
        destinations = [internal]
        if src.suffix.lower() == ".dll":
            destinations.append(app_dir)
        for dest_dir in destinations:
            dest = dest_dir / src.name
            try:
                if dest.exists() and dest.stat().st_size == src.stat().st_size:
                    if dest.resolve() == src.resolve():
                        continue
                    if dest.stat().st_size >= (MIN_PYTHON_DLL_BYTES if src.name.lower() == "python312.dll" else 1):
                        continue
                shutil.copy2(src, dest)
                copied.append(dest)
            except OSError:
                continue
    return copied


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    dest = Path(args[0] if args else "dist/WallpaperStudio")
    copied = copy_runtime_into(dest)
    print(f"copied {len(copied)} runtime files into {dest}")
    if sys.platform != "win32":
        return 0
    python_dll = dest / "_internal" / "python312.dll"
    if not python_dll.is_file() or python_dll.stat().st_size < MIN_PYTHON_DLL_BYTES:
        print(f"missing or tiny python312.dll: {python_dll}", file=sys.stderr)
        return 1
    for name in ("vcruntime140.dll", "vcruntime140_1.dll"):
        if not (dest / "_internal" / name).is_file() and not (dest / name).is_file():
            print(f"missing {name} next to the exe or in _internal", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
