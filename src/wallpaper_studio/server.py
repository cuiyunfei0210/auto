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

WEB_DIR = Path(__file__).resolve().parent / "web"


class StudioState:
    def __init__(self) -> None:
        self.task: asyncio.Task | None = None
        self.running = False
        self.logs: list[str] = []
        self.last_result: dict[str, Any] | None = None
        self.last_error: str | None = None
        self.subscribers: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def emit(self, message: str) -> None:
        self.logs.append(message)
        self.logs = self.logs[-400:]
        stale: list[WebSocket] = []
        for ws in list(self.subscribers):
            try:
                await ws.send_text(json.dumps({"type": "log", "message": message}))
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.subscribers.discard(ws)

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
        payload["source_count"] = len(list_images(source_dir(config)))
        payload["output_count"] = len(list_images(output_dir(config)))
        payload["source_dir"] = str(source_dir(config))
        payload["output_dir"] = str(output_dir(config))
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
            state.running = True
            state.last_error = None
            state.last_result = None
            state.logs = []
            state.task = asyncio.create_task(_run(config))
        await state.emit("任务已开始")
        return JSONResponse({"ok": True})

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
    try:
        result = await run_job(config, log=lambda message: asyncio.create_task(state.emit(message)))
        state.last_result = result
        await state.emit("任务完成")
    except asyncio.CancelledError:
        state.last_error = "已手动停止"
        await state.emit("任务已停止")
        raise
    except Exception as exc:  # noqa: BLE001
        state.last_error = str(exc)
        await state.emit(f"任务失败：{exc}")
    finally:
        state.running = False
        state.task = None
        stale = []
        for ws in list(state.subscribers):
            try:
                await ws.send_text(json.dumps({"type": "done", **state.snapshot()}))
            except Exception:
                stale.append(ws)
        for ws in stale:
            state.subscribers.discard(ws)


app = create_app()
