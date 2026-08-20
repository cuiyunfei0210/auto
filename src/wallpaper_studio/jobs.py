from __future__ import annotations

from collections.abc import Callable, Awaitable
from pathlib import Path

from wallpaper_studio.models import AppConfig
from wallpaper_studio.prepare import prepare_images
from wallpaper_studio.scheduler import plan_account_batches
from wallpaper_studio.uploader import upload_batches

LogFn = Callable[[str], None]


async def run_job(
    config: AppConfig,
    log: LogFn | None = None,
    sleep: Callable[[float], Awaitable[None]] | None = None,
    uploader=None,
    skip_prepare: bool = False,
    prepared: list[Path] | None = None,
) -> dict:
    emit = log or (lambda _message: None)
    if skip_prepare:
        images = list(prepared or [])
    else:
        emit("正在准备待上传图片…")
        images = prepare_images(config, emit)
    if not images:
        raise FileNotFoundError("没有可上传的图片。")
    if not config.accounts:
        raise ValueError("请至少添加一个账号。")

    batches = plan_account_batches(images, config.accounts, config.network)
    leftover = sum(len(batch.images) for batch in batches)
    unused = len(images) - leftover
    emit(f"共 {len(images)} 张图片，将依次使用 {len(batches)} 个账号")
    if unused > 0:
        emit(f"账号额度不够，有 {unused} 张图会留到下次")

    uploaded = await upload_batches(
        batches,
        config.site,
        log=emit,
        sleep=sleep,
        uploader=uploader,
    )
    emit(f"全部结束，成功上传 {uploaded} 张")
    return {
        "uploaded": uploaded,
        "accounts_used": len(batches),
        "image_count": len(images),
    }
