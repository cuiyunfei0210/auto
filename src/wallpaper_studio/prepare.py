from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from shutil import copy2

from wallpaper_studio.files import empty_source_message, list_images, sanitize_filename, unique_path
from wallpaper_studio.models import AppConfig
from wallpaper_studio.relay import ApiError, RelayClient, chat_model_supports_titles, friendly_error_message
from wallpaper_studio.storage import output_dir, source_dir

LogFn = Callable[[str], None]
ProgressFn = Callable[[int, int], None]


def prepare_images(
    config: AppConfig,
    log: LogFn | None = None,
    progress: ProgressFn | None = None,
) -> list[Path]:
    """Build the folder that will be uploaded.

    upload_only: images from the source folder, optionally renamed via API.
    remix_then_upload: call the relay image-edit API, save into the output folder.
    """
    emit = log or (lambda _message: None)
    src = source_dir(config)
    dest = output_dir(config)
    images = list_images(src)
    if not images:
        raise FileNotFoundError(empty_source_message(src))

    prepared: list[Path] = []
    client = RelayClient(config.api) if _needs_api(config) else None
    can_rename = (
        client is not None
        and config.api.filename_prompt.strip()
        and chat_model_supports_titles(config.api.filename_model)
    )
    if (
        client is not None
        and config.api.filename_prompt.strip()
        and not can_rename
    ):
        emit(
            f"文件名模型 {config.api.filename_model} 不能写标题，全部沿用原文件名"
        )

    remaining = len(images) if config.mode == "remix_then_upload" else 0
    total = remaining
    if progress:
        progress(remaining, total)
    if config.mode == "remix_then_upload":
        emit("二创会按提示词重绘样板；提示词留空时自动用默认改图词，不会原样照搬。")

    for image in images:
        title = image.stem
        if can_rename:
            assert client is not None
            try:
                title = client.generate_title(image.stem)
                emit(f"新文件名：{title}")
            except Exception as exc:  # noqa: BLE001 - keep going with original name
                emit(f"生成文件名失败，沿用原名 {image.stem}：{exc}")
                title = sanitize_filename(image.stem)

        title = sanitize_filename(title, fallback=image.stem)
        if config.mode == "remix_then_upload":
            assert client is not None
            emit(f"正在二创 {image.name} …")
            try:
                prepared.append(client.remix_image(image, dest, title))
            except ApiError as exc:
                raise ApiError(
                    f"{image.name} 二创失败。{friendly_error_message(str(exc))}"
                ) from exc
            emit(f"已保存二创结果 {prepared[-1].name}")
            remaining -= 1
            if progress:
                progress(remaining, total)
        else:
            target = unique_path(dest, title, image.suffix.lower())
            copy2(image, target)
            prepared.append(target)
            emit(f"待上传：{target.name}")
    return prepared


def _needs_api(config: AppConfig) -> bool:
    if config.mode == "remix_then_upload":
        return True
    has_secret = bool(
        config.api.api_key.strip()
        or (config.api.username.strip() and config.api.password)
    )
    return has_secret and bool(config.api.filename_prompt.strip())
