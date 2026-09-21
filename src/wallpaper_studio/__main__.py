from __future__ import annotations

import argparse
import os
import sys
import threading
import time
import traceback
from pathlib import Path

# Allow `python -m wallpaper_studio` from a source checkout.
if not getattr(sys, "frozen", False):
    ROOT = Path(__file__).resolve().parents[2]
    SRC = ROOT / "src"
    if (SRC / "wallpaper_studio").exists() and str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))


def main() -> None:
    parser = argparse.ArgumentParser(description="壁纸二创与顺序上传工具")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--web", action="store_true", help="用系统浏览器打开界面（调试）")
    parser.add_argument("--no-browser", action="store_true", help="只开后台服务，不打开窗口")
    parser.add_argument("--once", action="store_true", help="不打开界面，按当前配置跑一轮")
    args = parser.parse_args()

    from wallpaper_studio.browser import configure_playwright_env
    from wallpaper_studio.desktop import (
        DesktopWindowError,
        close_native_windows,
        open_native_window,
        should_open_native_window,
    )
    from wallpaper_studio.instance_lock import (
        InstanceLock,
        InstanceLockError,
        already_running_message,
        open_ui,
        wait_and_open_ui,
    )
    from wallpaper_studio.paths import app_root
    from wallpaper_studio.storage import load_config

    configure_playwright_env()
    os.chdir(app_root())
    _redirect_logs()

    if args.once:
        import asyncio
        from wallpaper_studio.jobs import run_job

        config = load_config()
        result = asyncio.run(run_job(config, log=print))
        print(result)
        return

    url = f"http://{args.host}:{args.port}"
    native = should_open_native_window(web=args.web, no_browser=args.no_browser)
    lock = InstanceLock()
    try:
        lock.acquire()
    except InstanceLockError:
        try:
            lock.take_over_stale(url)
            print("上次程序没有正常退出，已重新启动。")
        except InstanceLockError:
            print(already_running_message(url))
            _alert(already_running_message(url), icon="info")
            if args.web and not args.no_browser:
                open_ui(url)
            _pause_if_windows()
            sys.exit(1)

    try:
        import uvicorn
        from wallpaper_studio.server import app, runtime

        print()
        print("=" * 48)
        print("  壁纸工坊已启动")
        if native:
            print("  界面在程序窗口里，不打开系统浏览器。")
        elif args.web:
            print(f"  界面地址：{url}")
        else:
            print(f"  后台服务：{url}")
        print("=" * 48)
        print()
        config = uvicorn.Config(
            app,
            host=args.host,
            port=args.port,
            log_level="warning",
            access_log=False,
        )
        server = uvicorn.Server(config)
        server.install_signal_handlers = False
        runtime["server"] = server
        runtime["lock"] = lock
        runtime["close_ui"] = close_native_windows

        if native:
            worker = threading.Thread(target=server.run, name="studio-http", daemon=True)
            worker.start()

            def stop_server() -> None:
                server.should_exit = True

            try:
                open_native_window(url, on_closed=stop_server)
            except DesktopWindowError as exc:
                print(str(exc))
                _alert(str(exc))
                server.should_exit = True
                sys.exit(1)
            finally:
                server.should_exit = True
                worker.join(timeout=8)
            return

        if args.web:
            threading.Thread(target=wait_and_open_ui, args=(url,), daemon=True).start()
        server.run()
    except OSError as exc:
        print(f"无法启动界面服务：{exc}")
        print("请检查端口是否被占用，或在任务管理器结束 WallpaperStudio.exe 后再打开。")
        _alert(f"无法启动界面服务：{exc}\n请结束旧的 WallpaperStudio.exe 后再打开。")
        _pause_if_windows()
        sys.exit(1)
    except Exception:
        traceback.print_exc()
        _alert("壁纸工坊启动失败，请看 data\\studio.log")
        _pause_if_windows()
        sys.exit(1)
    finally:
        lock.release()


def _redirect_logs() -> None:
    from wallpaper_studio.paths import is_frozen

    if not is_frozen():
        return
    try:
        from wallpaper_studio.storage import data_dir

        handle = (data_dir() / "studio.log").open("a", encoding="utf-8", buffering=1)
        sys.stdout = handle
        sys.stderr = handle
    except OSError:
        pass


def _alert(message: str, icon: str = "error") -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        flags = 0x10 if icon == "error" else 0x40
        ctypes.windll.user32.MessageBoxW(0, str(message), "壁纸工坊", flags)
    except Exception:
        pass


def _pause_if_windows(seconds: float = 4) -> None:
    if os.name != "nt":
        return
    try:
        if sys.stdin and sys.stdin.isatty():
            input("按回车键退出…")
            return
    except Exception:
        pass
    time.sleep(seconds)


if __name__ == "__main__":
    main()
