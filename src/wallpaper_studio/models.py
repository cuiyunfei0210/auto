from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class ApiSettings(BaseModel):
    base_url: str = "https://api.newxxt.top"
    api_key: str = ""
    remix_model: str = "gpt-image-2"
    filename_model: str = "gpt-5.4-mini"
    remix_prompt: str = "Keep the same subject, restyle as a high-quality desktop wallpaper, cinematic lighting, sharp details."
    filename_prompt: str = "Write a short Chinese wallpaper title, max 18 characters, no file extension, no quotes."
    image_size: str = "1K"


class PathSettings(BaseModel):
    source_dir: str = ""
    output_dir: str = ""


class SiteProfile(BaseModel):
    """CSS selectors for a wallpaper site login + upload form."""

    login_url: str = "http://127.0.0.1:8765/demo/login"
    upload_url: str = "http://127.0.0.1:8765/demo/upload"
    username_selector: str = "#username"
    password_selector: str = "#password"
    login_button_selector: str = "button[type=submit]"
    file_input_selector: str = "input[type=file]"
    title_selector: str = "#title"
    category_selector: str = "#category"
    category_value: str = "风景"
    submit_selector: str = "#submit-upload"
    success_text: str = "上传成功"
    headless: bool = True
    navigation_timeout_ms: int = 30000


class Account(BaseModel):
    username: str
    password: str
    upload_count: int = Field(default=3, ge=1, le=500)
    interval_seconds: float = Field(default=8, ge=0, le=3600)

    @field_validator("username", "password")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("cannot be empty")
        return value


class NetworkSettings(BaseModel):
    proxy_enabled: bool = False
    rotate_every_accounts: int = Field(default=5, ge=1, le=100)
    proxies: list[str] = Field(default_factory=list)


class AppConfig(BaseModel):
    mode: str = "upload_only"  # upload_only | remix_then_upload
    api: ApiSettings = Field(default_factory=ApiSettings)
    paths: PathSettings = Field(default_factory=PathSettings)
    site: SiteProfile = Field(default_factory=SiteProfile)
    accounts: list[Account] = Field(
        default_factory=lambda: [
            Account(username="demo1", password="123123", upload_count=2, interval_seconds=2),
            Account(username="demo2", password="123123", upload_count=2, interval_seconds=2),
        ]
    )
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
