from __future__ import annotations

from collections.abc import Callable

from wallpaper_studio.control import JobStopped, stop_requested
from wallpaper_studio.files import (
    clear_images_in_dir,
    empty_source_message,
    image_dimensions,
    list_images,
    sanitize_filename,
)
from wallpaper_studio.models import AppConfig, PreparedImage, title_api_settings
from wallpaper_studio.relay import ApiError, RelayClient, friendly_error_message
from wallpaper_studio.storage import output_dir, source_dir

LogFn = Callable[[str], None]
ProgressFn = Callable[[int, int], None]
StopCheck = Callable[[], bool]


def prepare_images(
    config: AppConfig,
    log: LogFn | None = None,
    progress: ProgressFn | None = None,
    stop_check: StopCheck | None = None,
) -> list[PreparedImage]:
    """Build the list of images that will be uploaded.

    upload_only: upload files from the source folder in place (do not copy them).
    remix_then_upload: call the relay image-edit API, save into the output folder.
    """
    emit = log or (lambda _message: None)
    src = source_dir(config)
    dest = output_dir(config)
    images = list_images(src, exclude_roots=[dest])
    if not images:
        raise FileNotFoundError(empty_source_message(src))

    prepared: list[PreparedImage] = []
    remix_client = RelayClient(config.api) if config.mode == "remix_then_upload" else None
    title_settings = title_api_settings(config.api)
    title_client = None
    if config.api.filename_prompt.strip() and _has_api_secret(title_settings):
        if remix_client is not None and title_settings is config.api:
            title_client = remix_client
        else:
            title_client = RelayClient(title_settings)
    title_model = title_client.resolve_title_model() if title_client is not None else ""
    can_rename = bool(title_client is not None and title_model)
    if config.api.filename_prompt.strip() and not can_rename:
        emit(
            "根据图片写标题需要对话/识图模型。"
            f"当前填的是 {config.api.filename_model or '空'}。"
            "gpt-image-2 不能起名。newxxt 请填 gpt-5.4-mini；"
            "aipixapi / xmapi 这组 Key 只有生图，请把「写标题接口」改成 https://api.newxxt.top。"
        )

    remaining = len(images) if config.mode == "remix_then_upload" else 0
    total = remaining
    if progress:
        progress(remaining, total)
    if config.mode == "remix_then_upload":
        removed = clear_images_in_dir(dest)
        if removed:
            emit(f"已清空输出目录里上次留下的 {removed} 张图，本轮二创数量会和源图一致。")
        emit("二创会按你填的提示词改图，但原图分类不变：军事还是军事，动漫还是动漫，不会改成风景。不会强制黄昏；源图若是日落，请在提示词里写清要白天、阴天或夜晚。")

    def cancelled() -> bool:
        if stop_check and stop_check():
            return True
        return stop_requested()

    for image in images:
        if cancelled():
            emit("已停止，不再处理后续图片。")
            raise JobStopped("已手动停止")
        title = image.stem
        try:
            label = str(image.relative_to(src))
        except ValueError:
            label = image.name
        if can_rename:
            assert title_client is not None
            try:
                title = title_client.generate_title(image.stem, image)
                emit(f"新标题：{title}")
            except JobStopped:
                emit("已停止，不再处理后续图片。")
                raise
            except Exception as exc:  # noqa: BLE001 - keep going with original name
                emit(f"生成标题失败，沿用原名 {image.stem}：{exc}")
                title = sanitize_filename(image.stem)

        if cancelled():
            emit("已停止，不再处理后续图片。")
            raise JobStopped("已手动停止")
        title = sanitize_filename(title, fallback=image.stem)
        if config.mode == "remix_then_upload":
            assert remix_client is not None
            emit(f"正在二创 {label} …")
            try:
                remixed = remix_client.remix_image(image, dest, title)
            except JobStopped:
                emit("已停止，不再处理后续图片。")
                raise
            except ApiError as exc:
                raise ApiError(
                    f"{label} 二创失败。{friendly_error_message(str(exc))}"
                ) from exc
            category = remix_client.last_source_category
            prepared.append(PreparedImage(path=remixed, title=title, category=category))
            width, height = image_dimensions(remixed)
            if category:
                emit(f"已保存二创结果 {remixed.name}（标题：{title}，分类：{category}，{width}×{height}）")
            else:
                emit(f"已保存二创结果 {remixed.name}（标题：{title}，{width}×{height}）")
            remaining -= 1
            if progress:
                progress(remaining, total)
        else:
            prepared.append(PreparedImage(path=image, title=title))
            emit(f"待上传：{image.name}（标题：{title}）")
    return prepared


def _has_api_secret(settings) -> bool:
    return bool(
        settings.api_key.strip()
        or settings.filename_api_key.strip()
        or (settings.username.strip() and settings.password)
    )


def _needs_api(config: AppConfig) -> bool:
    if config.mode == "remix_then_upload":
        return True
    return _has_api_secret(config.api) and bool(config.api.filename_prompt.strip())
