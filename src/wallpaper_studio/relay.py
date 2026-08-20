from __future__ import annotations

import base64
import mimetypes
import re
import time
from pathlib import Path

import httpx

from wallpaper_studio.files import sanitize_filename, unique_path
from wallpaper_studio.models import ApiSettings

_MD_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
_DATA_URL = re.compile(r"^data:image/([^;]+);base64,(.+)$", re.DOTALL | re.IGNORECASE)


class ApiError(RuntimeError):
    pass


def friendly_error_message(raw: str) -> str:
    """Turn known relay/API failures into an actionable Chinese explanation."""
    text = (raw or "").strip()
    if "中转站的 /v1/images" in text or "中转站生图接口" in text or "中转站已关闭批量生图" in text:
        return text
    lowered = text.lower()
    if "image_generation" in lowered and "tools" in lowered:
        return (
            "中转站的 /v1/images 生图通道仍在报 Tool choice 'image_generation' not found in 'tools' parameter。"
            "程序已改走干净的 /v1/images/edits（生图模型用 gpt-image-2），对话模型请填这个 Key 组实际有的模型。"
            "当前这组 Key 常见只有 gpt-image-2，不能用来写标题。实在不行再暂时改用「跳过二创」。"
        )
    if "xmapi.site" in lowered and ("生图" in text or "images" in lowered or "线路" in text):
        return (
            "当前接口走的是 xbhuiz 线路，不能生图。请把接口地址改成 https://xmapi.site （不要带 /v1），"
            "API Key 用中转站后台给的 sk-，生图模型填 gpt-image-2。"
        )
    if "temporarily unavailable" in lowered or "upstream service" in lowered or "upstream_error" in lowered:
        return (
            "中转站上游生图暂时不可用（Upstream service temporarily unavailable）。"
            "这是 xmapi 后面的模型线路抖动，不是图片或账号填错。"
            "程序会自动重试几次；若仍然失败，等一两分钟再跑，或先改用「跳过二创」。"
        )
    if "batch_image_disabled" in lowered or "batch image" in lowered:
        return (
            "中转站已关闭批量生图接口。请改成「跳过二创，直接上传」，或换一组能用的图片模型。"
        )
    return text or "未知错误"


def normalize_api_base(url: str) -> str:
    text = (url or "").strip().rstrip("/")
    if text.lower().endswith("/v1"):
        text = text[:-3].rstrip("/")
    return text or "https://xmapi.site"


def resolve_api_key(settings: ApiSettings, transport: httpx.BaseTransport | None = None) -> str:
    if settings.api_key.strip():
        return settings.api_key.strip()
    email = settings.username.strip()
    password = settings.password
    if not email or not password:
        raise ApiError("还没有填写 API Key，也没有中转站邮箱密码。")
    base = normalize_api_base(settings.base_url)
    kwargs: dict = {"timeout": 30.0}
    if transport is not None:
        kwargs["transport"] = transport
    with httpx.Client(**kwargs) as client:
        login = client.post(
            f"{base}/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        data = _json_or_error(login)
        token = ""
        if isinstance(data, dict):
            inner = data.get("data") if isinstance(data.get("data"), dict) else data
            token = str((inner or {}).get("access_token") or "")
        if not token:
            raise ApiError("中转站登录成功，但没有返回 access_token。")
        keys = client.get(
            f"{base}/api/v1/keys",
            headers={"Authorization": f"Bearer {token}"},
        )
        payload = _json_or_error(keys)
        items = []
        if isinstance(payload, dict):
            inner = payload.get("data")
            if isinstance(inner, dict):
                items = inner.get("items") or inner.get("keys") or []
            elif isinstance(inner, list):
                items = inner
        active = [
            item.get("key")
            for item in items
            if isinstance(item, dict)
            and item.get("key")
            and str(item.get("status") or "active").lower() in {"", "active", "enabled", "1"}
        ]
        if not active:
            raise ApiError("中转站账号下没有可用的 API Key，请先在网站里创建一个。")
        return str(active[0])


def chat_model_supports_titles(model: str) -> bool:
    """gpt-image-2 and similar image models reject /v1/chat/completions."""
    name = (model or "").strip().lower()
    if not name:
        return False
    markers = ("image", "dall-e", "dalle", "flux", "midjourney", "stable-diffusion", "sdxl")
    return not any(token in name for token in markers)


def is_transient_relay_error(text: str) -> bool:
    lowered = (text or "").lower()
    tokens = (
        "temporarily unavailable",
        "upstream service",
        "upstream_error",
        "overloaded",
        "bad gateway",
        "gateway timeout",
        "timed out",
        "service unavailable",
        "502",
        "503",
        "504",
    )
    return any(token in lowered for token in tokens)


def official_image_size(value: str) -> str:
    text = (value or "").strip() or "1024x1024"
    key = text.lower().replace(" ", "").replace("×", "x")
    mapping = {
        "1k": "1024x1024",
        "2k": "1536x1024",
        "4k": "1536x1024",
        "auto": "auto",
        "square": "1024x1024",
        "portrait": "1024x1536",
        "landscape": "1536x1024",
    }
    return mapping.get(key, text.replace("×", "x"))


class RelayClient:
    def __init__(
        self,
        settings: ApiSettings,
        timeout: float = 240.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self.timeout = timeout
        self.transport = transport
        self._resolved_key: str | None = None

    def _headers(self) -> dict[str, str]:
        if not self._resolved_key:
            self._resolved_key = resolve_api_key(self.settings, transport=self.transport)
        return {
            "Authorization": f"Bearer {self._resolved_key}",
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        return normalize_api_base(self.settings.base_url) + path

    def _chat_model(self) -> str:
        return (
            self.settings.remix_chat_model.strip()
            or self.settings.filename_model.strip()
            or "gpt-image-2"
        )

    def _post_json(
        self,
        path: str,
        payload: dict,
        timeout: float | None = None,
        retries: int = 0,
    ) -> dict:
        kwargs: dict = {"timeout": self.timeout if timeout is None else timeout}
        if self.transport is not None:
            kwargs["transport"] = self.transport
        last_error: Exception | None = None
        attempts = max(1, retries + 1)
        for attempt in range(attempts):
            try:
                with httpx.Client(**kwargs) as client:
                    response = client.post(
                        self._url(path),
                        headers=self._headers(),
                        json=payload,
                    )
                return _json_or_error(response)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = ApiError(f"中转站网络超时或中断：{exc}")
            except ApiError as exc:
                last_error = exc
                if not is_transient_relay_error(str(exc)):
                    raise
            if attempt + 1 >= attempts:
                break
            time.sleep(2 * (attempt + 1))
        assert last_error is not None
        raise last_error

    def generate_title(self, original_stem: str) -> str:
        if not chat_model_supports_titles(self.settings.filename_model):
            raise ApiError(
                f"文件名模型 {self.settings.filename_model} 不支持对话接口，无法自动起名。"
            )
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
        data = self._post_json("/v1/chat/completions", payload, timeout=20.0)
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
        errors: list[str] = []
        for path, payload in self._remix_requests(data_url, mime):
            try:
                data = self._post_json(path, payload, retries=3)
                image_bytes, suffix = extract_image_payload(data, source.suffix)
            except ApiError as exc:
                errors.append(f"{path}: {exc}")
                continue
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = unique_path(dest_dir, title, suffix)
            dest.write_bytes(image_bytes)
            return dest
        combined = " | ".join(errors) if errors else "未知错误"
        raise ApiError(friendly_error_message(combined))

    def _remix_requests(self, data_url: str, mime: str) -> list[tuple[str, dict]]:
        prompt = self.settings.remix_prompt.strip() or "Restyle this image as a desktop wallpaper."
        prompt = (
            "You must generate an edited wallpaper image from the reference photo. "
            "Do not reply with text only.\n"
            + prompt
        )
        chat_model = self._chat_model()
        image_model = self.settings.remix_model.strip() or "gpt-image-2"
        size = official_image_size(self.settings.image_size)
        edits = (
            "/v1/images/edits",
            {
                "model": image_model,
                "prompt": prompt,
                "images": [{"image_url": data_url}],
                "size": size,
            },
        )
        if not chat_model_supports_titles(chat_model):
            # gpt-image-2 is not a chat model. xmapi.site accepts a clean edits payload;
            # responses/chat on this key return 503 / "not supported".
            return [edits]
        tool = {
            "type": "image_generation",
            "action": "edit",
            "size": size,
        }
        return [
            (
                "/v1/responses",
                {
                    "model": chat_model,
                    "input": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": prompt},
                                {
                                    "type": "input_image",
                                    "image_url": data_url,
                                    "detail": "auto",
                                },
                            ],
                        }
                    ],
                    "tools": [tool],
                    "tool_choice": "auto",
                },
            ),
            (
                "/v1/chat/completions",
                {
                    "model": chat_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": data_url}},
                            ],
                        }
                    ],
                    "tools": [{"type": "image_generation", "size": size}],
                    "tool_choice": "auto",
                    "modalities": ["text", "image"],
                },
            ),
            edits,
        ]


def _json_or_error(response: httpx.Response) -> dict:
    try:
        data = response.json()
    except ValueError as exc:
        raise ApiError(f"接口返回了非 JSON 内容（HTTP {response.status_code}）。") from exc
    if response.status_code >= 400:
        message = _error_message(data) or f"HTTP {response.status_code}"
        raise ApiError(friendly_error_message(message))
    if isinstance(data, dict) and data.get("error"):
        raise ApiError(friendly_error_message(_error_message(data)))
    return data if isinstance(data, dict) else {"data": data}


def _error_message(data: dict) -> str:
    error = data.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error.get("code") or error)
    if error:
        return str(error)
    return str(data.get("message") or "")


def extract_image_payload(data: dict, fallback_suffix: str) -> tuple[bytes, str]:
    found = _first_image_bytes(data)
    if found:
        return found[0], found[1] or fallback_suffix or ".png"
    raise ApiError("生图接口没有返回图片数据。")


def _first_image_bytes(data: object) -> tuple[bytes, str] | None:
    if isinstance(data, dict):
        items = data.get("data")
        if isinstance(items, list):
            for item in items:
                found = _image_from_mapping(item) if isinstance(item, dict) else None
                if found:
                    return found
        for item in data.get("output") or []:
            found = _first_image_bytes(item)
            if found:
                return found
        if data.get("type") == "image_generation_call" or data.get("result"):
            found = _image_from_mapping(data)
            if found:
                return found
        message = data.get("choices")
        if isinstance(message, list):
            for choice in message:
                if isinstance(choice, dict):
                    found = _first_image_bytes(choice.get("message") or choice)
                    if found:
                        return found
        for key in ("message", "content", "images"):
            if key in data:
                found = _first_image_bytes(data.get(key))
                if found:
                    return found
        found = _image_from_mapping(data)
        if found:
            return found
    if isinstance(data, list):
        for item in data:
            found = _first_image_bytes(item)
            if found:
                return found
    if isinstance(data, str):
        return _image_from_text(data)
    return None


def _image_from_mapping(item: dict) -> tuple[bytes, str] | None:
    for key in ("b64_json", "b64", "result"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            decoded = _decode_image_text(value, allow_short=True)
            if decoded:
                return decoded
    url = item.get("url") or item.get("image_url")
    if isinstance(url, dict):
        url = url.get("url")
    if isinstance(url, str) and url.strip():
        return _image_from_text(url)
    return None


def _image_from_text(text: str) -> tuple[bytes, str] | None:
    match = _MD_IMAGE.search(text)
    if match:
        return _image_from_text(match.group(1).strip(" '\""))
    return _decode_image_text(text)


def _decode_image_text(text: str, allow_short: bool = False) -> tuple[bytes, str] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    data_url = _DATA_URL.match(raw)
    if data_url:
        suffix = "." + data_url.group(1).lower().replace("jpeg", "jpg")
        return base64.b64decode(data_url.group(2)), suffix
    if raw.startswith("http://") or raw.startswith("https://"):
        image = httpx.get(raw, timeout=60.0)
        image.raise_for_status()
        suffix = Path(raw.split("?")[0]).suffix or ".png"
        return image.content, suffix
    if (allow_short or len(raw) > 80) and re.fullmatch(r"[A-Za-z0-9+/=\s]+", raw):
        try:
            blob = base64.b64decode(raw)
        except Exception:
            return None
        if blob:
            return blob, ".png"
    return None
