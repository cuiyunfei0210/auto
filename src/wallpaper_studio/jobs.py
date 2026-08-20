from __future__ import annotations

import asyncio
from collections.abc import Callable, Awaitable
from pathlib import Path

from wallpaper_studio.models import AppConfig
from wallpaper_studio.prepare import prepare_images
from wallpaper_studio.scheduler import plan_account_batches
from wallpaper_studio.uploader import upload_batches

LogFn = Callable[[str], None]
ProgressFn = Callable[[int, int], None]


async def run_job(
    config: AppConfig,
    log: LogFn | None = None,
    sleep: Callable[[float], Awaitable[None]] | None = None,
    uploader=None,
    skip_prepare: bool = False,
    prepared: list[Path] | None = None,
    progress: ProgressFn | None = None,
) -> dict:
    emit = log or (lambda _message: None)
    if not config.accounts:
        raise ValueError("还没有添加账号。请先到「账号」页填 cqwall 邮箱和密码，再开始任务。")
    if skip_prepare:
        images = list(prepared or [])
    else:
        emit("正在准备待上传图片…")
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            images = prepare_images(config, emit, progress)
        else:
            images = await asyncio.to_thread(prepare_images, config, emit, progress)
    if not images:
        raise FileNotFoundError("没有可上传的图片。")

    batches = plan_account_batches(images, config.accounts, config.network)
    leftover = sum(len(batch.images) for batch in batches)
    unused = len(images) - leftover
    emit(f"共 {len(images)} 张图片，将依次使用 {len(batches)} 个账号")
    if unused > 0:
        emit(f"账号额度不够，有 {unused} 张图会留到下次")
    if config.network.proxy_enabled:
        for batch in batches:
            exit_label = batch.proxy or "直连"
            emit(f"账号 {batch.account.username} 出口：{exit_label}")
    elif len(batches) > 1:
        emit("未启用代理，本轮多个账号会走当前同一出口。需要分开时请为每个账号准备一个代理。")

    uploaded, skipped = await upload_batches(
        batches,
        config.site,
        log=emit,
        sleep=sleep,
        uploader=uploader,
    )
    if skipped:
        emit(f"全部结束，成功上传 {uploaded} 张，跳过 {skipped} 张")
    else:
        emit(f"全部结束，成功上传 {uploaded} 张")
    return {
        "uploaded": uploaded,
        "skipped": skipped,
        "accounts_used": len(batches),
        "image_count": len(images),
    }
