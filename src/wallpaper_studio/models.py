from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

DEFAULT_REMIX_PROMPT = (
    "根据参考图做二创：必须保留原图的主体、人物、装备、场景类型和构图。"
    "原图如果是军事/士兵/武器/战机，结果也必须是军事，禁止改成风景、城市广场、街道或只有建筑的空镜头。"
    "原图如果是人物或动漫角色，必须保留同一类角色，禁止改成风景。"
    "只改画质、光线、色调和细节，不要换题材。禁止原样复制像素。"
    "不要默认做成黄昏、日落或金橙色晚霞，除非提示词明确要求。"
    " Restyle this reference. Keep the same subject, people, gear, and scene type. "
    "Military stays military; characters stay characters. Never replace the subject "
    "with landscape, cityscape, plaza, or architecture-only scenery. "
    "Change lighting and detail only. Do not copy the original pixels. "
    "Do not default to sunset, dusk, or golden hour unless the prompt asks for it."
)
_WEAK_REMIX_PROMPTS = {
    "Keep the same subject, restyle as a high-quality desktop wallpaper, cinematic lighting, sharp details.",
    "Restyle this image as a desktop wallpaper.",
    (
        "根据参考图做一张全新的高质量桌面壁纸。保留主体，但必须按提示改光线、色调和氛围，禁止原样复制。"
        "锐利细节，没有水印和文字。"
        "不要默认做成黄昏、日落或金橙色晚霞，除非提示词明确要求。"
        " Create a brand-new desktop wallpaper from this reference. Keep the subject, "
        "but change lighting and mood as instructed. Do not copy the original pixels "
        "or return a near-identical image. Sharp details, no watermarks. "
        "Do not default to sunset, dusk, or golden hour unless the prompt asks for it."
    ),
    (
        "把这张参考图做成一张全新的高质量桌面壁纸。"
        "保留主体和构图，但必须明显改变光线、色调、材质、细节和氛围，"
        "禁止原样复制或输出几乎不变的图。"
        "电影级光影，锐利细节，没有水印和文字。 "
        "Create a brand-new high-quality desktop wallpaper from this reference image. "
        "Keep the same subject and composition, but you MUST clearly change lighting, "
        "color grade, textures, details, and atmosphere. Do not copy the original pixels "
        "or return a near-identical image. Cinematic lighting, sharp details, no watermarks or text."
    ),
}


def effective_remix_prompt(value: str | None) -> str:
    """Blank or leftover built-in prompts get a default. User text is kept as-is."""
    text = (value or "").strip()
    if not text or text in _WEAK_REMIX_PROMPTS:
        return DEFAULT_REMIX_PROMPT
    return text


NEWXXT_API_BASE = "https://api.newxxt.top"
OLD_NEWXXT_API_KEYS = {
    "sk-beef6174c1f75a4eec5a5890a1f4ed02a3d4824ec72962cb51960d66d577c927",
}
NEWXXT_API_KEY = "sk-ac87085afeb3d0fcf7574c86f021d5421d1f690b9dbcd1358aa9ec85ead98e29"
NEWXXT_CHAT_KEY = "sk-dcaeb94ce3a1dd94713f43d844776a122d152585f34e7f136f62577cca3a618f"
DEFAULT_CHAT_MODEL = "gpt-5.4-mini"
DEFAULT_IMAGE_MODEL = "gpt-image-2"
DEFAULT_FILENAME_PROMPT = (
    "Write a short English wallpaper title, max 18 characters, no file extension, no quotes."
)
_OLD_FILENAME_PROMPTS = {
    "Write a short Chinese wallpaper title, max 18 characters, no file extension, no quotes.",
}


def upgrade_filename_prompt(value: str | None) -> str:
    """Keep a blank prompt blank (skip titles). Replace the old Chinese default."""
    text = value if value is not None else ""
    if text.strip() in _OLD_FILENAME_PROMPTS:
        return DEFAULT_FILENAME_PROMPT
    return text


class ApiSettings(BaseModel):
    base_url: str = NEWXXT_API_BASE
    api_key: str = NEWXXT_API_KEY
    username: str = ""
    password: str = ""
    remix_model: str = DEFAULT_IMAGE_MODEL
    remix_chat_model: str = DEFAULT_IMAGE_MODEL
    filename_model: str = DEFAULT_CHAT_MODEL
    filename_base_url: str = ""
    filename_api_key: str = ""
    remix_prompt: str = DEFAULT_REMIX_PROMPT
    filename_prompt: str = DEFAULT_FILENAME_PROMPT
    image_size: str = "1920x1080"

    @field_validator("remix_prompt", mode="before")
    @classmethod
    def fill_blank_remix_prompt(cls, value: object) -> object:
        if value is None:
            return DEFAULT_REMIX_PROMPT
        if isinstance(value, str):
            return effective_remix_prompt(value)
        return value

    @field_validator("filename_prompt", mode="before")
    @classmethod
    def upgrade_old_filename_prompt(cls, value: object) -> object:
        if isinstance(value, str):
            return upgrade_filename_prompt(value)
        return value


class PathSettings(BaseModel):
    source_dir: str = ""
    output_dir: str = ""


class SiteProfile(BaseModel):
    """CSS selectors for a wallpaper site login + upload form."""

    login_url: str = "https://www.cqwall.com/"
    upload_url: str = "https://www.cqwall.com/index/index/center.html"
    open_login_selector: str = ""
    username_selector: str = '#layer-user input[name="email"]'
    password_selector: str = '#layer-user input[name="password"]'
    login_button_selector: str = '#layer-user button[lay-filter="login"]'
    login_success_text: str = ""
    logged_in_selector: str = ""
    open_upload_selector: str = ""
    file_input_selector: str = "input[type=file]"
    file_uploaded_text: str = ""
    title_selector: str = '#layer-upload input[name="title"]'
    category_selector: str = '#layer-upload select[name="category"]'
    category_value: str = "9"
    agree_selector: str = ""
    submit_selector: str = '#layer-upload button[lay-filter="wallpaper"]'
    success_text: str = ""
    min_width: int = 0
    min_height: int = 0
    headless: bool = True
    navigation_timeout_ms: int = 45000

    @field_validator("min_width", "min_height")
    @classmethod
    def no_image_size_limit(cls, _value: int) -> int:
        return 0


class Account(BaseModel):
    username: str
    password: str
    upload_count: int = Field(default=3, ge=1, le=500)
    interval_seconds: float = Field(default=8, ge=0, le=3600)
    proxy: str | None = None

    @field_validator("username", "password")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("cannot be empty")
        return value

    @field_validator("proxy", mode="before")
    @classmethod
    def empty_proxy(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class NetworkSettings(BaseModel):
    proxy_enabled: bool = False
    unique_ip_per_account: bool = True
    rotate_every_accounts: int = Field(default=1, ge=1, le=100)
    proxies: list[str] = Field(default_factory=list)


def default_site_profile() -> SiteProfile:
    from wallpaper_studio.sites import cqwall_site

    return cqwall_site()


def default_accounts() -> list[Account]:
    return [
        Account(
            username="ari-ihcot@linshi-mail.com",
            password="123123123",
            upload_count=3,
            interval_seconds=8,
        )
    ]


RELAY_EMAILS_IN_CQWALL_SLOT = {"1252597792@qq.com", "596003517@qq.com"}
DEFAULT_API_BASE = NEWXXT_API_BASE
DEFAULT_API_KEY = NEWXXT_API_KEY


def _relay_root(url: str) -> str:
    text = (url or "").strip().rstrip("/").lower()
    if text.endswith("/v1"):
        text = text[:-3].rstrip("/")
    return text


def title_api_settings(settings: ApiSettings) -> ApiSettings:
    """Titles can use a second newxxt Key while remix stays on the image Key."""
    base = (settings.filename_base_url or "").strip() or settings.base_url
    key = (settings.filename_api_key or "").strip() or settings.api_key
    if _relay_root(base) == _relay_root(settings.base_url) and key == settings.api_key:
        return settings
    return settings.model_copy(update={"base_url": base, "api_key": key})


def apply_builtin_defaults(config: "AppConfig") -> "AppConfig":
    """Fill empty/legacy fields with CQwall accounts and lock the API host to newxxt."""
    payload = config.model_dump()
    changed = False
    accounts = [
        item
        for item in (payload.get("accounts") or [])
        if str(item.get("username") or "").strip().lower() not in RELAY_EMAILS_IN_CQWALL_SLOT
    ]
    if accounts != payload.get("accounts"):
        payload["accounts"] = accounts
        changed = True
    if not accounts:
        payload["accounts"] = [item.model_dump() for item in default_accounts()]
        changed = True
    api = payload.setdefault("api", {})
    wanted_url = _relay_root(NEWXXT_API_BASE)
    current_url = _relay_root(str(api.get("base_url") or ""))
    current_key = str(api.get("api_key") or "").strip()
    if current_url != wanted_url:
        api["base_url"] = NEWXXT_API_BASE
        api["api_key"] = NEWXXT_API_KEY
        current_key = NEWXXT_API_KEY
        if not str(api.get("filename_api_key") or "").strip():
            api["filename_api_key"] = NEWXXT_CHAT_KEY
        api["filename_base_url"] = ""
        changed = True
    elif current_key in OLD_NEWXXT_API_KEYS:
        api["api_key"] = NEWXXT_API_KEY
        current_key = NEWXXT_API_KEY
        if not str(api.get("filename_api_key") or "").strip():
            api["filename_api_key"] = NEWXXT_CHAT_KEY
        changed = True
    elif not current_key:
        api["api_key"] = NEWXXT_API_KEY
        current_key = NEWXXT_API_KEY
        changed = True
    title_url = _relay_root(str(api.get("filename_base_url") or ""))
    if title_url and title_url != wanted_url:
        api["filename_base_url"] = ""
        changed = True
    if not str(api.get("remix_model") or "").strip():
        api["remix_model"] = DEFAULT_IMAGE_MODEL
        changed = True
    if not str(api.get("remix_chat_model") or "").strip():
        api["remix_chat_model"] = DEFAULT_IMAGE_MODEL
        changed = True
    if not str(api.get("filename_model") or "").strip():
        api["filename_model"] = DEFAULT_CHAT_MODEL
        changed = True
    prompt = effective_remix_prompt(str(api.get("remix_prompt") or ""))
    if prompt != str(api.get("remix_prompt") or ""):
        api["remix_prompt"] = prompt
        changed = True
    filename_prompt = upgrade_filename_prompt(str(api.get("filename_prompt") or ""))
    if filename_prompt != str(api.get("filename_prompt") or ""):
        api["filename_prompt"] = filename_prompt
        changed = True
    if not changed:
        return config
    return AppConfig.model_validate(payload)


class AppConfig(BaseModel):
    mode: str = "upload_only"  # upload_only | remix_then_upload
    upload_category: str = ""  # CQwall Chinese label chosen on the task pane
    api: ApiSettings = Field(default_factory=ApiSettings)
    paths: PathSettings = Field(default_factory=PathSettings)
    site: SiteProfile = Field(default_factory=default_site_profile)
    accounts: list[Account] = Field(default_factory=default_accounts)
    network: NetworkSettings = Field(default_factory=NetworkSettings)

    @field_validator("mode")
    @classmethod
    def valid_mode(cls, value: str) -> str:
        allowed = {"upload_only", "remix_then_upload"}
        if value not in allowed:
            raise ValueError(f"mode must be one of {sorted(allowed)}")
        return value


class UploadTask(BaseModel):
    account_username: str
    image_path: str
    title: str
    category: str = ""
    interval_seconds: float = 0
    proxy: str | None = None


@dataclass(frozen=True)
class PreparedImage:
    path: Path
    title: str
    category: str = ""


class AccountBatch(BaseModel):
    account: Account
    images: list[PreparedImage]
    proxy: str | None = None

    model_config = {"arbitrary_types_allowed": True}
