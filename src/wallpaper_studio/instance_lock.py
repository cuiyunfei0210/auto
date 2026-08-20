from __future__ import annotations

import os
import socket

from wallpaper_studio.storage import data_dir


class InstanceLockError(RuntimeError):
    pass


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
        lock_path = data_dir() / "instance.lock"
        lock_path.write_text(str(self.port), encoding="utf-8")

    def release(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None
