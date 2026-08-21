from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import time
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from wallpaper_studio.storage import data_dir


class InstanceLockError(RuntimeError):
    pass


def already_running_message(url: str) -> str:
    return (
        "程序已经在运行，同一台电脑只能打开一次。\n"
        "请到任务栏点「壁纸工坊」窗口。\n"
        "如果看不到窗口，请打开任务管理器结束 WallpaperStudio.exe，再重新双击。"
        "不要反复双击 exe。"
    )


def ui_is_reachable(url: str, timeout: float = 0.6) -> bool:
    """True when the studio HTTP server actually answers."""
    target = (url or "").rstrip("/") + "/api/health"
    try:
        request = Request(target, method="GET")
        with urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", None) or response.getcode()
            return 200 <= int(status) < 500
    except (OSError, URLError, ValueError, TimeoutError):
        return False


def open_ui(url: str) -> None:
    try:
        if os.name == "nt":
            os.startfile(url)  # type: ignore[attr-defined]
            return
    except OSError:
        pass
    webbrowser.open(url)


def wait_and_open_ui(url: str, retries: int = 40, delay: float = 0.25) -> None:
    """Open the browser only after the local UI port is actually answering."""
    for _ in range(max(1, retries)):
        if ui_is_reachable(url):
            open_ui(url)
            return
        time.sleep(delay)
    open_ui(url)


class InstanceLock:
    """Bind a local lock port so the studio cannot be opened twice."""

    def __init__(self, port: int | None = None) -> None:
        self.port = port or int(os.environ.get("WALLPAPER_STUDIO_LOCK_PORT", "18765"))
        self._socket: socket.socket | None = None

    def acquire(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", self.port))
        except OSError as exc:
            sock.close()
            raise InstanceLockError("程序已经在运行，同一台电脑只能打开一次。") from exc
        sock.listen(1)
        self._socket = sock
        self._write_lock_file()

    def take_over_stale(self, ui_url: str, grace_seconds: float = 2.5) -> None:
        """If a previous run died while holding the lock, kill it and bind again."""
        if ui_is_reachable(ui_url):
            raise InstanceLockError("程序已经在运行，同一台电脑只能打开一次。")
        deadline = time.time() + max(0.0, grace_seconds)
        while time.time() < deadline:
            time.sleep(0.25)
            if ui_is_reachable(ui_url):
                raise InstanceLockError("程序已经在运行，同一台电脑只能打开一次。")
            try:
                self.acquire()
                return
            except InstanceLockError:
                continue
        info = _read_lock_info()
        pid = int(info.get("pid") or 0)
        if pid and pid != os.getpid() and _pid_is_running(pid):
            _terminate_pid(pid)
            for _ in range(25):
                if not _pid_is_running(pid):
                    break
                time.sleep(0.1)
        self.acquire()

    def release(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        try:
            _lock_path().unlink(missing_ok=True)
        except OSError:
            pass

    def _write_lock_file(self) -> None:
        try:
            path = _lock_path()
            path.write_text(
                json.dumps({"port": self.port, "pid": os.getpid()}),
                encoding="utf-8",
            )
        except OSError:
            pass


def _lock_path() -> Path:
    return data_dir() / "instance.lock"


def _read_lock_info() -> dict:
    path = _lock_path()
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return {}
    if not text:
        return {}
    if text.startswith("{"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    info: dict = {}
    if lines and lines[0].isdigit():
        info["port"] = int(lines[0])
    if len(lines) > 1 and lines[1].isdigit():
        info["pid"] = int(lines[1])
    return info


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        return _windows_pid_is_running(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _windows_pid_is_running(pid: int) -> bool:
    import ctypes

    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    process_query_limited_information = 0x1000
    handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
    if handle:
        kernel32.CloseHandle(handle)
        return True
    return False


def _terminate_pid(pid: int) -> None:
    if pid <= 0 or pid == os.getpid():
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            check=False,
            capture_output=True,
        )
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
