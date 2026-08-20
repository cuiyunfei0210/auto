from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_validator

DEFAULT_REMIX_PROMPT = (
    "把这张参考图做成一张全新的高质量桌面壁纸。"
    "保留主体和构图，但必须明显改变光线、色调、材质、细节和氛围，"
    "禁止原样复制或输出几乎不变的图。"
    "电影级光影，锐利细节，没有水印和文字。 "
    "Create a brand-new high-quality desktop wallpaper from this reference image. "
    "Keep the same subject and composition, but you MUST clearly change lighting, "
    "color grade, textures, details, and atmosphere. Do not copy the original pixels "
    "or return a near-identical image. Cinematic lighting, sharp details, no watermarks or text."
)
_WEAK_REMIX_PROMPTS = {
    "Keep the same subject, restyle as a high-quality desktop wallpaper, cinematic lighting, sharp details.",
    "Restyle this image as a desktop wallpaper.",
}


def effective_remix_prompt(value: str | None) -> str:
    """Blank or leftover weak prompts must restyle, not copy the template."""
    text = (value or "").strip()
    if not text or text in _WEAK_REMIX_PROMPTS:
        return DEFAULT_REMIX_PROMPT
    return text


class ApiSettings(BaseModel):
    base_url: str = "https://xmapi.site"
    api_key: str = "sk-8a77cad546b762802c03bf0afaa41b5a68d3962d2ec939188bf64a6f1d5337df"
    username: str = "596003517@qq.com"
    password: str = "123123"
    remix_model: str = "gpt-image-2"
    remix_chat_model: str = "gpt-image-2"
    filename_model: str = "gpt-image-2"
    remix_prompt: str = DEFAULT_REMIX_PROMPT
    filename_prompt: str = "Write a short Chinese wallpaper title, max 18 characters, no file extension, no quotes."
    image_size: str = "1K"

    @field_validator("remix_prompt", mode="before")
    @classmethod
    def fill_blank_remix_prompt(cls, value: object) -> object:
        if value is None:
            return DEFAULT_REMIX_PROMPT
        if isinstance(value, str):
            return effective_remix_prompt(value)
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


OLD_RELAY_URLS = {
    "https://api.newxxt.top",
    "https://xbhuiz.com",
    "https://www.xbhuiz.com",
}
RELAY_EMAILS_IN_CQWALL_SLOT = {"1252597792@qq.com", "596003517@qq.com"}
DEFAULT_API_BASE = "https://xmapi.site"
DEFAULT_API_KEY = "sk-8a77cad546b762802c03bf0afaa41b5a68d3962d2ec939188bf64a6f1d5337df"


def _relay_root(url: str) -> str:
    text = (url or "").strip().rstrip("/").lower()
    if text.endswith("/v1"):
        text = text[:-3].rstrip("/")
    return text


def apply_builtin_defaults(config: "AppConfig") -> "AppConfig":
    """Fill empty/legacy fields with the built-in CQwall + xmapi defaults."""
    payload = config.model_dump()
    changed = False
    wanted = "ari-ihcot@linshi-mail.com"
    accounts = [
        item
        for item in (payload.get("accounts") or [])
        if str(item.get("username") or "").strip().lower() not in RELAY_EMAILS_IN_CQWALL_SLOT
    ]
    if accounts != payload.get("accounts"):
        payload["accounts"] = accounts
        changed = True
    names = {str(item.get("username") or "").strip().lower() for item in accounts}
    if wanted.lower() not in names:
        payload["accounts"] = [item.model_dump() for item in default_accounts()] + accounts
        changed = True
    api = payload.setdefault("api", {})
    current_url = _relay_root(str(api.get("base_url") or ""))
    if not current_url or current_url in {_relay_root(item) for item in OLD_RELAY_URLS}:
        api["base_url"] = DEFAULT_API_BASE
        if not str(api.get("api_key") or "").strip():
            api["api_key"] = DEFAULT_API_KEY
        changed = True
    elif current_url == _relay_root(DEFAULT_API_BASE) and not str(api.get("api_key") or "").strip():
        api["api_key"] = DEFAULT_API_KEY
        changed = True
    if not str(api.get("username") or "").strip():
        api["username"] = "596003517@qq.com"
        if not str(api.get("password") or "").strip():
            api["password"] = "123123"
        changed = True
    prompt = effective_remix_prompt(str(api.get("remix_prompt") or ""))
    if prompt != str(api.get("remix_prompt") or ""):
        api["remix_prompt"] = prompt
        changed = True
    if not changed:
        return config
    return AppConfig.model_validate(payload)


class AppConfig(BaseModel):
    mode: str = "upload_only"  # upload_only | remix_then_upload
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


class AccountBatch(BaseModel):
    account: Account
    images: list[Path]
    proxy: str | None = None

    model_config = {"arbitrary_types_allowed": True}
