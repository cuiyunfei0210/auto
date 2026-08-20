from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from wallpaper_studio import __version__
from wallpaper_studio.demo_site import demo_router
from wallpaper_studio.jobs import run_job
from wallpaper_studio.models import AppConfig
from wallpaper_studio.storage import load_config, save_config, source_dir, output_dir
from wallpaper_studio.files import list_images
from wallpaper_studio.scheduler import ProxyAssignmentError, preview_proxy_assignments
from wallpaper_studio.sites import SITE_PRESETS
from wallpaper_studio.paths import archive_temp_warning, web_dir
from wallpaper_studio.relay import friendly_error_message

WEB_DIR = web_dir()


class StudioState:
    def __init__(self) -> None:
        self.task: asyncio.Task | None = None
        self.running = False
        self.logs: list[str] = []
        self.last_result: dict[str, Any] | None = None
        self.last_error: str | None = None
        self.subscribers: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    def note(self, message: str) -> None:
        """Record a log line immediately so later failure text cannot jump ahead."""
        text = (message or "").strip()
        if not text:
            return
        self.logs.append(text)
        self.logs = self.logs[-400:]

    async def send_event(self, payload: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        raw = json.dumps(payload)
        for ws in list(self.subscribers):
            try:
                await ws.send_text(raw)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.subscribers.discard(ws)

    async def broadcast(self, message: str) -> None:
        await self.send_event({"type": "log", "message": message})

    async def emit(self, message: str) -> None:
        self.note(message)
        await self.broadcast(message)

    def snapshot(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "logs": self.logs[-200:],
            "last_result": self.last_result,
            "last_error": self.last_error,
            "version": __version__,
        }


state = StudioState()


def create_app() -> FastAPI:
    app = FastAPI(title="Wallpaper Studio", version=__version__)
    app.include_router(demo_router)
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/api/state")
    async def api_state() -> JSONResponse:
        config = load_config()
        payload = state.snapshot()
        payload["config"] = config.model_dump()
        payload["presets"] = {name: profile.model_dump() for name, profile in SITE_PRESETS.items()}
        payload["source_count"] = len(list_images(source_dir(config)))
        payload["output_count"] = len(list_images(output_dir(config)))
        payload["source_dir"] = str(source_dir(config))
        payload["output_dir"] = str(output_dir(config))
        try:
            payload["proxy_assignments"] = preview_proxy_assignments(config.accounts, config.network)
            payload["proxy_error"] = None
        except ProxyAssignmentError as exc:
            payload["proxy_assignments"] = []
            payload["proxy_error"] = str(exc)
        payload["archive_warning"] = archive_temp_warning()
        return JSONResponse(payload)

    @app.post("/api/config")
    async def api_save_config(payload: dict[str, Any]) -> JSONResponse:
        try:
            config = AppConfig.model_validate(payload)
        except ValidationError as exc:
            return JSONResponse({"ok": False, "error": exc.errors()}, status_code=400)
        save_config(config)
        return JSONResponse({"ok": True, "config": config.model_dump()})

    @app.post("/api/start")
    async def api_start() -> JSONResponse:
        async with state._lock:
            if state.running:
                return JSONResponse({"ok": False, "error": "任务正在运行"}, status_code=409)
            config = load_config()
            if not config.accounts:
                return JSONResponse(
                    {
                        "ok": False,
                        "error": "还没有添加账号。请先到「账号」页填 cqwall 邮箱和密码，再开始任务。",
                    },
                    status_code=400,
                )
            try:
                preview_proxy_assignments(config.accounts, config.network)
            except ProxyAssignmentError as exc:
                return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
            state.running = True
            state.last_error = None
            state.last_result = None
            state.logs = []
            state.note("任务已开始")
            state.task = asyncio.create_task(_run(config))
        await state.send_event({"type": "reset", "logs": state.logs, "running": True})
        return JSONResponse({"ok": True, "logs": list(state.logs)})

    @app.post("/api/stop")
    async def api_stop() -> JSONResponse:
        task = state.task
        if task and not task.done():
            task.cancel()
            await state.emit("正在停止…")
        return JSONResponse({"ok": True})

    @app.websocket("/ws")
    async def websocket_logs(ws: WebSocket) -> None:
        await ws.accept()
        state.subscribers.add(ws)
        try:
            await ws.send_text(json.dumps({"type": "hello", **state.snapshot()}))
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            state.subscribers.discard(ws)

    return app


async def _run(config: AppConfig) -> None:
    loop = asyncio.get_running_loop()
    broadcasts: list[asyncio.Task] = []

    def schedule_broadcast(text: str) -> None:
        broadcasts.append(asyncio.create_task(state.broadcast(text)))

    def log(message: str) -> None:
        state.note(message)
        loop.call_soon_threadsafe(schedule_broadcast, message)

    async def flush_logs() -> None:
        await asyncio.sleep(0)
        if broadcasts:
            await asyncio.gather(*broadcasts)
            broadcasts.clear()

    try:
        result = await run_job(config, log=log)
        await flush_logs()
        state.last_result = result
        await state.emit("任务完成")
    except asyncio.CancelledError:
        await flush_logs()
        state.last_error = "已手动停止"
        await state.emit("任务已停止")
        raise
    except Exception as exc:  # noqa: BLE001
        await flush_logs()
        message = friendly_error_message(str(exc)).lstrip(": ").strip()
        state.last_error = message
        await state.emit(f"任务失败：{message}")
    finally:
        state.running = False
        state.task = None
        await state.send_event({"type": "done", **state.snapshot()})


app = create_app()
