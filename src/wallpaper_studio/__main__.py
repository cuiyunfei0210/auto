from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path
import sys

# Allow `python -m wallpaper_studio` from a source checkout.
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if (SRC / "wallpaper_studio").exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> None:
    parser = argparse.ArgumentParser(description="壁纸二创与顺序上传工具")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--once", action="store_true", help="不打开界面，按当前配置跑一轮")
    args = parser.parse_args()

    from wallpaper_studio.instance_lock import InstanceLock, InstanceLockError
    from wallpaper_studio.storage import load_config

    if args.once:
        import asyncio
        from wallpaper_studio.jobs import run_job

        config = load_config()
        result = asyncio.run(run_job(config, log=print))
        print(result)
        return

    lock = InstanceLock()
    try:
        lock.acquire()
    except InstanceLockError as exc:
        print(exc)
        sys.exit(1)

    try:
        import uvicorn
        from wallpaper_studio.server import app

        if not args.no_browser:
            url = f"http://{args.host}:{args.port}"
            webbrowser.open(url)
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    finally:
        lock.release()


if __name__ == "__main__":
    main()
