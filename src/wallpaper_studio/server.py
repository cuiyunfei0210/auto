from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from wallpaper_studio import __version__
from wallpaper_studio.demo_site import demo_router
from wallpaper_studio.jobs import run_job
from wallpaper_studio.models import AppConfig
from wallpaper_studio.storage import (
    load_config,
    output_dir_status,
    save_config,
    source_dir_status,
)
from wallpaper_studio.files import empty_source_message, list_images
from wallpaper_studio.scheduler import ProxyAssignmentError, preview_proxy_assignments
from wallpaper_studio.sites import SITE_PRESETS
from wallpaper_studio.paths import archive_temp_warning, web_dir
from wallpaper_studio.relay import friendly_error_message
from wallpaper_studio.preflight import format_start_problems, start_problems

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
        self.remix_remaining: int | None = None
        self.remix_total: int | None = None

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
            "remix_pending": self.remix_remaining,
            "remix_total": self.remix_total,
            "version": __version__,
        }


state = StudioState()


def create_app() -> FastAPI:
    app = FastAPI(title="Wallpaper Studio", version=__version__)
    app.include_router(demo_router)

    @app.get("/static/studio.js")
    async def studio_js() -> FileResponse:
        return FileResponse(WEB_DIR / "studio.js", media_type="text/javascript; charset=utf-8")

    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.exception_handler(Exception)
    async def json_unhandled(_request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, WebSocketDisconnect):
            raise exc
        return JSONResponse({"ok": False, "error": f"程序内部错误：{exc}"}, status_code=500)

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/api/state")
    async def api_state() -> JSONResponse:
        try:
            config = load_config()
            payload = state.snapshot()
            payload["config"] = config.model_dump()
            payload["presets"] = {name: profile.model_dump() for name, profile in SITE_PRESETS.items()}
            src, src_note = source_dir_status(config)
            dest, dest_note = output_dir_status(config)
            try:
                images = list_images(src)
            except Exception as exc:  # noqa: BLE001
                images = []
                src_note = src_note or f"无法扫描源目录 {src}：{exc}"
            try:
                output_images = list_images(dest)
            except Exception:  # noqa: BLE001
                output_images = []
            payload["source_count"] = len(images)
            payload["output_count"] = len(output_images)
            if state.running and state.remix_remaining is not None:
                payload["remix_pending"] = state.remix_remaining
                payload["remix_total"] = state.remix_total if state.remix_total is not None else state.remix_remaining
            elif config.mode == "remix_then_upload":
                payload["remix_pending"] = len(images)
                payload["remix_total"] = len(images)
            else:
                payload["remix_pending"] = 0
                payload["remix_total"] = 0
            payload["source_dir"] = str(src)
            payload["output_dir"] = str(dest)
            payload["source_note"] = src_note or ("" if images else empty_source_message(src))
            if dest_note and not payload["source_note"]:
                payload["source_note"] = dest_note
            payload["source_samples"] = [path.name for path in images[:8]]
            try:
                payload["proxy_assignments"] = preview_proxy_assignments(config.accounts, config.network)
                payload["proxy_error"] = None
            except ProxyAssignmentError as exc:
                payload["proxy_assignments"] = []
                payload["proxy_error"] = str(exc)
            payload["archive_warning"] = archive_temp_warning()
            return JSONResponse(payload)
        except Exception as exc:  # noqa: BLE001 - the UI must always get JSON
            return JSONResponse(
                {
                    "ok": False,
                    "error": f"程序内部错误：{exc}",
                    "running": False,
                    "logs": [f"程序内部错误：{exc}"],
                    "source_count": 0,
                    "output_count": 0,
                    "remix_pending": 0,
                    "remix_total": 0,
                    "source_dir": "",
                    "output_dir": "",
                    "source_note": f"程序内部错误：{exc}",
                    "source_samples": [],
                    "config": {},
                    "presets": {},
                },
                status_code=500,
            )

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
            problems = start_problems(config)
            if problems:
                return JSONResponse(
                    {
                        "ok": False,
                        "error": format_start_problems(problems),
                        "problems": problems,
                    },
                    status_code=400,
                )
            state.running = True
            state.last_error = None
            state.last_result = None
            state.logs = []
            if config.mode == "remix_then_upload":
                src, _note = source_dir_status(config)
                try:
                    pending = len(list_images(src))
                except Exception:
                    pending = 0
                state.remix_remaining = pending
                state.remix_total = pending
            else:
                state.remix_remaining = 0
                state.remix_total = 0
            state.note("任务已开始")
            state.task = asyncio.create_task(_run(config))
        await state.send_event({
            "type": "reset",
            "logs": state.logs,
            "running": True,
            "remix_pending": state.remix_remaining,
            "remix_total": state.remix_total,
        })
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

    def progress(remaining: int, total: int) -> None:
        state.remix_remaining = remaining
        state.remix_total = total

        def emit_progress(left: int = remaining, all_count: int = total) -> None:
            broadcasts.append(
                asyncio.create_task(
                    state.send_event(
                        {
                            "type": "remix_progress",
                            "remaining": left,
                            "total": all_count,
                            "remix_pending": left,
                        }
                    )
                )
            )

        loop.call_soon_threadsafe(emit_progress)

    async def flush_logs() -> None:
        await asyncio.sleep(0)
        if broadcasts:
            await asyncio.gather(*broadcasts)
            broadcasts.clear()

    try:
        result = await run_job(config, log=log, progress=progress)
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
        state.remix_remaining = None
        state.remix_total = None
        await state.send_event({"type": "done", **state.snapshot()})


app = create_app()
