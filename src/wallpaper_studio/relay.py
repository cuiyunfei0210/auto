from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

import httpx

from wallpaper_studio.files import sanitize_filename, unique_path
from wallpaper_studio.models import ApiSettings


class ApiError(RuntimeError):
    pass


class RelayClient:
    def __init__(self, settings: ApiSettings, timeout: float = 180.0) -> None:
        self.settings = settings
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        key = self.settings.api_key.strip()
        if not key:
            raise ApiError("还没有填写 API Key。")
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        return self.settings.base_url.rstrip("/") + path

    def generate_title(self, original_stem: str) -> str:
        prompt = self.settings.filename_prompt.strip() or "Generate a short wallpaper title."
        payload = {
            "model": self.settings.filename_model,
            "messages": [
                {
                    "role": "system",
                    "content": "Return only the title text. No quotes, no file extension.",
                },
                {
                    "role": "user",
                    "content": f"{prompt}\nOriginal filename: {original_stem}",
                },
            ],
            "max_tokens": 64,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                self._url("/v1/chat/completions"),
                headers=self._headers(),
                json=payload,
            )
        data = _json_or_error(response)
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ApiError("文件名接口返回格式无法解析。") from exc
        return sanitize_filename(str(text), fallback=original_stem)

    def remix_image(self, source: Path, dest_dir: Path, title: str) -> Path:
        mime = mimetypes.guess_type(source.name)[0] or "image/png"
        raw = source.read_bytes()
        encoded = base64.b64encode(raw).decode("ascii")
        data_url = f"data:{mime};base64,{encoded}"
        payload = {
            "model": self.settings.remix_model,
            "prompt": self.settings.remix_prompt,
            "image_size": self.settings.image_size,
            "size": self.settings.image_size,
            "images": [{"image_url": data_url, "mime_type": mime}],
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                self._url("/v1/images/edits"),
                headers=self._headers(),
                json=payload,
            )
        data = _json_or_error(response)
        image_bytes, suffix = _extract_image(data, source.suffix)
        dest = unique_path(dest_dir, title, suffix)
        dest.write_bytes(image_bytes)
        return dest


def _json_or_error(response: httpx.Response) -> dict:
    try:
        data = response.json()
    except ValueError as exc:
        raise ApiError(f"接口返回了非 JSON 内容（HTTP {response.status_code}）。") from exc
    if response.status_code >= 400:
        message = _error_message(data) or f"HTTP {response.status_code}"
        raise ApiError(message)
    if isinstance(data, dict) and data.get("error"):
        raise ApiError(_error_message(data))
    return data if isinstance(data, dict) else {"data": data}


def _error_message(data: dict) -> str:
    error = data.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error.get("code") or error)
    if error:
        return str(error)
    return str(data.get("message") or "")


def _extract_image(data: dict, fallback_suffix: str) -> tuple[bytes, str]:
    items = data.get("data")
    if isinstance(items, list) and items:
        item = items[0]
        if isinstance(item, dict):
            b64 = item.get("b64_json") or item.get("b64")
            if b64:
                return base64.b64decode(b64), fallback_suffix or ".png"
            url = item.get("url")
            if url:
                image = httpx.get(url, timeout=60.0)
                image.raise_for_status()
                suffix = Path(url.split("?")[0]).suffix or fallback_suffix or ".png"
                return image.content, suffix
    raise ApiError("生图接口没有返回图片数据。")
