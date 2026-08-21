from __future__ import annotations

import sys
import time
from collections.abc import Callable
from typing import Any

from wallpaper_studio.instance_lock import ui_is_reachable

WEBVIEW2_URL = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"


class DesktopWindowError(RuntimeError):
    pass


def should_open_native_window(*, web: bool, no_browser: bool) -> bool:
    """Default is a real app window. --web uses the system browser; --no-browser is server-only."""
    return not web and not no_browser


def wait_until_up(url: str, timeout: float = 20.0, pause: float = 0.1) -> None:
    deadline = time.time() + max(0.2, timeout)
    while time.time() < deadline:
        if ui_is_reachable(url):
            return
        time.sleep(pause)
    raise DesktopWindowError("界面服务启动超时，程序窗口打不开。")


def close_native_windows() -> None:
    try:
        import webview
    except Exception:
        return
    for window in list(getattr(webview, "windows", []) or []):
        try:
            window.destroy()
        except Exception:
            pass


def open_native_window(
    url: str,
    title: str = "壁纸工坊",
    on_closed: Callable[[], None] | None = None,
) -> None:
    """Block the main thread with a native window that loads the local studio UI."""
    try:
        import webview
    except ImportError as exc:
        raise DesktopWindowError(
            "缺少桌面窗口组件。请重新下载完整的 WallpaperStudio 文件夹。"
        ) from exc

    wait_until_up(url)
    window = webview.create_window(
        title,
        url,
        width=1280,
        height=840,
        min_size=(960, 640),
        background_color="#14120F",
        text_select=True,
        easy_drag=False,
    )
    if on_closed is not None:
        try:
            window.events.closed += lambda: on_closed()
        except Exception:
            pass

    start_kwargs: dict[str, Any] = {}
    if sys.platform == "win32":
        start_kwargs["gui"] = "edgechromium"
    try:
        webview.start(**start_kwargs)
    except Exception as exc:
        text = str(exc)
        if sys.platform == "win32" and (
            "webview2" in text.lower()
            or "web view" in text.lower()
            or "edgechromium" in text.lower()
        ):
            raise DesktopWindowError(
                "打不开程序窗口。请安装 Microsoft Edge WebView2 运行库后再打开：\n"
                f"{WEBVIEW2_URL}"
            ) from exc
        raise DesktopWindowError(f"打不开程序窗口：{exc}") from exc
