from __future__ import annotations

from wallpaper_studio.files import list_images
from wallpaper_studio.models import AppConfig
from wallpaper_studio.paths import archive_temp_warning
from wallpaper_studio.scheduler import ProxyAssignmentError, preview_proxy_assignments
from wallpaper_studio.storage import source_dir


def start_problems(config: AppConfig) -> list[str]:
    """Return human-readable blockers that should stop a job from starting."""
    problems: list[str] = []
    warning = archive_temp_warning()
    if warning:
        problems.append(warning)
    if not config.accounts:
        problems.append("还没有账号。请到「账号」页填写 CQwall 邮箱和密码。")
    if not (config.site.login_url or "").strip():
        problems.append("网页上传的登录地址是空的。请到「网页上传」检查。")
    if not (config.site.username_selector or "").strip() or not (config.site.password_selector or "").strip():
        problems.append("网页上传的账号或密码选择器是空的。请到「网页上传」检查。")
    images = list_images(source_dir(config))
    if not images:
        problems.append(f"源文件夹里没有图片：{source_dir(config)}。请到「文件夹」确认源目录。")
    if config.mode == "remix_then_upload":
        has_secret = bool(
            config.api.api_key.strip()
            or (config.api.username.strip() and config.api.password)
        )
        if not (config.api.base_url or "").strip():
            problems.append("二创模式需要填写中转站接口地址，例如 https://xmapi.site（不要带 /v1）。")
        if not has_secret:
            problems.append("二创模式需要 API Key，或中转站邮箱和密码。请到「二创 API」填写。")
        if not (config.api.remix_model or "").strip():
            problems.append("二创模式需要填写生图模型。当前这组 Key 一般用 gpt-image-2。")
    try:
        preview_proxy_assignments(config.accounts, config.network)
    except ProxyAssignmentError as exc:
        problems.append(str(exc))
    return problems


def format_start_problems(problems: list[str]) -> str:
    if len(problems) == 1:
        return problems[0]
    return "还不能开始，请先处理：\n" + "\n".join(f"{index}. {item}" for index, item in enumerate(problems, start=1))
