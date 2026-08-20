from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class ApiSettings(BaseModel):
    base_url: str = "https://xbhuiz.com"
    api_key: str = ""
    username: str = "596003517@qq.com"
    password: str = "123123"
    remix_model: str = "gpt-image-2"
    remix_chat_model: str = "gpt-image-2"
    filename_model: str = "gpt-image-2"
    remix_prompt: str = "Keep the same subject, restyle as a high-quality desktop wallpaper, cinematic lighting, sharp details."
    filename_prompt: str = "Write a short Chinese wallpaper title, max 18 characters, no file extension, no quotes."
    image_size: str = "1K"


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


OLD_RELAY_URLS = {"https://api.newxxt.top"}
RELAY_EMAILS_IN_CQWALL_SLOT = {"1252597792@qq.com", "596003517@qq.com"}


def apply_builtin_defaults(config: "AppConfig") -> "AppConfig":
    """Fill empty/legacy fields with the built-in CQwall + xbhuiz defaults."""
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
    current_url = str(api.get("base_url") or "").strip().rstrip("/")
    if not current_url or current_url in OLD_RELAY_URLS:
        api["base_url"] = "https://xbhuiz.com"
        api["api_key"] = ""
        changed = True
    if not str(api.get("username") or "").strip():
        api["username"] = "596003517@qq.com"
        if not str(api.get("password") or "").strip():
            api["password"] = "123123"
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
