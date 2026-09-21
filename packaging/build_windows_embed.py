"""Build a portable Windows folder using CPython's official embeddable runtime.

PyInstaller's bootloader LoadLibrary's ``_internal\\python312.dll`` and shows:

    Failed to load Python DLL ... python312.dll
    LoadLibrary: 找不到指定的模块。

That dialog is from the PyInstaller stub, not from Python itself. The embeddable
zip ships python312.dll next to pythonw.exe and vcruntime140.dll — the layout
python.org supports for redistribution.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EMBED_VERSION = "3.12.10"
EMBED_URL = f"https://www.python.org/ftp/python/{EMBED_VERSION}/python-{EMBED_VERSION}-embed-amd64.zip"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {url}")
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url) as response, dest.open("wb") as handle:
                shutil.copyfileobj(response, handle)
            return
        except Exception as exc:  # noqa: BLE001 - retry network flakes
            last_error = exc
            print(f"download failed ({attempt + 1}/4): {exc}")
            time.sleep(2 ** attempt)
    raise RuntimeError(f"failed to download {url}: {last_error}") from last_error


def _csc() -> Path:
    windir = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    candidates = [
        windir / "Microsoft.NET" / "Framework64" / "v4.0.30319" / "csc.exe",
        windir / "Microsoft.NET" / "Framework" / "v4.0.30319" / "csc.exe",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise SystemExit("csc.exe not found; need .NET Framework 4 to compile WallpaperStudio.exe")


def _write_pth(embed_dir: Path) -> None:
    pth = embed_dir / "python312._pth"
    pth.write_text("python312.zip\n.\nLib\\site-packages\nimport site\n", encoding="utf-8")


LAUNCHER_BAT_NAMES = ("1-打开壁纸工坊.bat", "打开壁纸工坊.bat")


def _copy_launcher_bats(dest: Path) -> None:
    bat = ROOT / "packaging" / "open-studio.bat"
    if not bat.is_file():
        return
    for name in LAUNCHER_BAT_NAMES:
        shutil.copy2(bat, dest / name)


def clean_for_delivery(dest: Path) -> None:
    """Drop headers, smoke-test leftovers, and other files that hide the exe."""
    dest = Path(dest)
    for name in ("Include", "data", "Scripts"):
        path = dest / name
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
    for name in ("launcher.log", "smoke-out.txt", "smoke-err.txt", "get-pip.py"):
        path = dest / name
        if path.is_file():
            path.unlink(missing_ok=True)


def _compile_launcher(embed_dir: Path) -> None:
    csc = _csc()
    launcher = ROOT / "packaging" / "launcher.cs"
    out = embed_dir / "WallpaperStudio.exe"
    cmd = [str(csc), "/nologo", "/target:winexe", "/platform:x64", f"/out:{out}", str(launcher)]
    print(" ".join(cmd))
    subprocess.check_call(cmd)


def build(dest: Path | None = None) -> Path:
    if sys.platform != "win32":
        raise SystemExit("Windows embeddable build must run on Windows")
    dest = Path(dest or (ROOT / "dist" / "WallpaperStudio"))
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    (dest / "Lib" / "site-packages").mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="ws-embed-") as tmp:
        tmp_path = Path(tmp)
        zip_path = tmp_path / "python-embed.zip"
        _download(EMBED_URL, zip_path)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(dest)

    _write_pth(dest)
    python = dest / "python.exe"
    get_pip = dest / "get-pip.py"
    _download(GET_PIP_URL, get_pip)
    subprocess.check_call([str(python), str(get_pip), "--no-warn-script-location"])
    get_pip.unlink(missing_ok=True)
    subprocess.check_call(
        [str(python), "-m", "pip", "install", "--upgrade", "--no-warn-script-location", "setuptools", "wheel"]
    )
    subprocess.check_call(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--no-build-isolation",
            "--no-warn-script-location",
            str(ROOT),
        ]
    )

    shutil.copy2(ROOT / "run.py", dest / "run.py")
    readme = ROOT / "packaging" / "exe-readme.txt"
    if readme.exists():
        shutil.copy2(readme, dest / "使用说明.txt")
    _copy_launcher_bats(dest)
    clean_for_delivery(dest)

    sys.path.insert(0, str(ROOT / "packaging"))
    from windows_runtime import copy_crt_dlls

    copied = copy_crt_dlls(dest)
    print(f"copied {len(copied)} CRT DLLs into {dest}")

    _compile_launcher(dest)
    python_dll = dest / "python312.dll"
    if not python_dll.is_file() or python_dll.stat().st_size < 1_000_000:
        raise SystemExit(f"python312.dll missing from embed package: {python_dll}")
    if not (dest / "vcruntime140.dll").is_file():
        raise SystemExit("vcruntime140.dll missing from embed package")
    if not (dest / "WallpaperStudio.exe").is_file():
        raise SystemExit("WallpaperStudio.exe failed to compile")
    print(f"built {dest}")
    return dest


def main() -> int:
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "WallpaperStudio"
    build(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
