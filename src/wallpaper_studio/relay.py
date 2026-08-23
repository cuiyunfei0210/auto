from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path

import httpx

from wallpaper_studio.control import JobStopped, pop_http, push_http, stop_requested, wait_or_stop
from wallpaper_studio.files import fit_image_bytes, sanitize_filename, unique_path
from wallpaper_studio.models import (
    AIPIX_API_BASE,
    AIPIX_API_KEY,
    ApiSettings,
    DEFAULT_API_BASE,
    effective_remix_prompt,
    title_api_settings,
)

_MD_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
_DATA_URL = re.compile(r"^data:image/([^;]+);base64,(.+)$", re.DOTALL | re.IGNORECASE)


class ApiError(RuntimeError):
    pass


def friendly_error_message(raw: str) -> str:
    """Turn known relay/API failures into an actionable Chinese explanation."""
    text = (raw or "").strip()
    if "中转站的 /v1/images" in text or "中转站生图接口" in text or "中转站已关闭批量生图" in text or "中转站没有可用的生图线路" in text:
        return text
    lowered = text.lower()
    if "not supported by any configured account" in lowered or "model_not_found" in lowered:
        return (
            "这个中转站的 Key 组没有该模型。"
            "生图请用 gpt-image-2；写标题请用 gpt-5.4-mini，接口用 https://api.newxxt.top（不要带 /v1）。"
            "aipixapi 这组 Key 只有 gpt-image-2，不能起名。"
        )
    if "image generation is not enabled" in lowered:
        return (
            "当前这组 Key 是对话组，不能生图。"
            "「生图 API Key」请填中转站里名称带「生图」的那把，"
            "「对话 API Key」请填名称带「对话」的那把。"
        )
    if "image_generation" in lowered and "tools" in lowered:
        return (
            "中转站后台「测试账号」走的是 /v1/images/generations（文生图，不带原图），"
            "能出小狗照片只说明文生图通了，不能说明二创通了。"
            "壁纸工坊二创要按原图改图，会打 /v1/images/edits；"
            "这条改图通道仍在报 Tool choice 'image_generation' not found in 'tools'。"
            "请让中转站给 gpt-image-2 打开「改图 / images/edits」。"
            "程序会先走改图；改图不通才会先识图再文生图，并且会锁定原图主体。"
            "不会在没看过原图时直接文生图，否则军事会变成风景。"
            "这个站的文生图线路会抖动，后台刚测通小狗，程序这边有时仍会被转进坏掉的 tools 通道。"
            "请再跑一次；还不行就暂时改用「跳过二创」。"
        )
    if "xmapi.site" in lowered and ("生图" in text or "images" in lowered or "线路" in text):
        return (
            "当前接口走的是 xbhuiz 线路，不能生图。请把接口地址改成 https://api.newxxt.top 或 https://www.aipixapi.art （不要带 /v1），"
            "生图模型填 gpt-image-2。写标题用 newxxt 的 gpt-5.4-mini。"
        )
    if "temporarily unavailable" in lowered or "upstream service" in lowered or "upstream_error" in lowered:
        return (
            "中转站上游生图暂时不可用（Upstream service temporarily unavailable）。"
            "这是 xmapi 后面的模型线路抖动，不是图片或账号填错。"
            "程序会自动重试几次；若仍然失败，等一两分钟再跑，或先改用「跳过二创」。"
        )
    if "no available compatible accounts" in lowered or "no available accounts" in lowered:
        return (
            "中转站没有可用的生图线路（No available compatible accounts）。"
            "这是 xmapi 这组 Key 后面没有能跑 gpt-image-2 / 图编辑的账号，不是 CQwall、也不是本地图片坏了。"
            "请到中转站后台看这组 Key 是否还能生图、额度是否用完；或先改用「跳过二创，直接上传」。"
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
    return text or DEFAULT_API_BASE


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


def _is_tools_choice_error(text: str) -> bool:
    lowered = (text or "").lower()
    return "image_generation" in lowered and "tools" in lowered


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


MAX_OUTPUT_SIDE = 7680


def official_image_size(value: str) -> str:
    api_size, _upscale = resolve_remix_size(value)
    return api_size


def resolve_remix_size(value: str) -> tuple[str, tuple[int, int] | None]:
    """Map UI size to gpt-image-2's native size plus an exact output size.

    gpt-image-2 only generates 1024x1024, 1536x1024, or 1024x1536. Configured
    sizes such as 1920x1080 are generated at the nearest native size, then
    resized with LANCZOS so the saved file matches what the user filled in.
    """
    text = (value or "").strip() or "1920x1080"
    key = text.lower().replace(" ", "").replace("×", "x")
    mapping: dict[str, tuple[str, tuple[int, int] | None]] = {
        "1k": ("1024x1024", None),
        "1024x1024": ("1024x1024", None),
        "square": ("1024x1024", None),
        "auto": ("auto", None),
        "1536x1024": ("1536x1024", None),
        "landscape": ("1536x1024", (1920, 1080)),
        "2k": ("1536x1024", (2560, 1440)),
        "qhd": ("1536x1024", (2560, 1440)),
        "2560x1440": ("1536x1024", (2560, 1440)),
        "1080p": ("1536x1024", (1920, 1080)),
        "fhd": ("1536x1024", (1920, 1080)),
        "1920x1080": ("1536x1024", (1920, 1080)),
        "4k": ("1536x1024", (3840, 2160)),
        "uhd": ("1536x1024", (3840, 2160)),
        "3840x2160": ("1536x1024", (3840, 2160)),
        "portrait": ("1024x1536", (1080, 1920)),
        "1024x1536": ("1024x1536", None),
        "1080x1920": ("1024x1536", (1080, 1920)),
        "9:16": ("1024x1536", (1080, 1920)),
        "16:9": ("1536x1024", (1920, 1080)),
    }
    if key in mapping:
        return mapping[key]
    parsed = _parse_width_height(key)
    if parsed:
        width, height = parsed
        api_size = _nearest_official_size(width, height)
        api_w, api_h = (int(part) for part in api_size.split("x"))
        if (width, height) == (api_w, api_h):
            return api_size, None
        return api_size, (width, height)
    return "1536x1024", (1920, 1080)


def _parse_width_height(text: str) -> tuple[int, int] | None:
    if "x" not in text:
        return None
    left, right = text.split("x", 1)
    if not left.isdigit() or not right.isdigit():
        return None
    width, height = int(left), int(right)
    if width < 256 or height < 256:
        return None
    return min(width, MAX_OUTPUT_SIDE), min(height, MAX_OUTPUT_SIDE)


def _nearest_official_size(width: int, height: int) -> str:
    if abs(width - height) < min(width, height) * 0.08:
        return "1024x1024"
    if height > width:
        return "1024x1536"
    return "1536x1024"


_SUNSET_HINTS = (
    "黄昏",
    "日落",
    "夕阳",
    "晚霞",
    "金色小时",
    "sunset",
    "dusk",
    "twilight",
    "golden hour",
    "golden-hour",
)


def prompt_asks_for_sunset(text: str) -> bool:
    raw = text or ""
    lowered = raw.lower()
    for token in _SUNSET_HINTS:
        haystack = lowered if token.isascii() else raw
        needle = token.lower() if token.isascii() else token
        start = 0
        while True:
            pos = haystack.find(needle, start)
            if pos < 0:
                break
            prefix = haystack[max(0, pos - 8) : pos]
            if any(
                marker in prefix
                for marker in ("不要", "别", "禁止", "避免", "not ", "no ", "don't", "do not", "dont")
            ):
                start = pos + len(needle)
                continue
            return True
    return False


SUBJECT_LOCK = (
    "Hard subject lock: keep the reference photo's actual subject and category. "
    "If the source shows soldiers, weapons, aircraft, or tactics, the result MUST stay military. "
    "If it shows a person or anime character, keep that character. "
    "Never turn people or military scenes into landscape, European streets, city squares, "
    "or architecture-only scenery.\n"
)


def build_remix_prompt(user_prompt: str) -> str:
    instruction = effective_remix_prompt(user_prompt)
    extra = ""
    if not prompt_asks_for_sunset(instruction):
        extra = (
            "Do not default to sunset, dusk, golden hour, or orange evening light "
            "unless the instruction above explicitly asks for it. "
            "Follow the requested time of day and color mood; if none is specified, "
            "use natural daylight that is clearly different from the reference photo.\n"
        )
    return (
        f"Primary instruction:\n{instruction}\n\n"
        "Edit the attached reference photo. Do not invent a new scene from the text alone. "
        "The instruction above may change lighting and mood, but must not replace the subject. "
        "Do not reply with text only, and do not return the original image unchanged.\n"
        + SUBJECT_LOCK
        + extra
    )


def _generation_prompt_from_description(description: str, user_prompt: str) -> str:
    instruction = effective_remix_prompt(user_prompt)
    scene = (description or "").strip()
    return (
        f"Create a restyled version of this exact scene:\n{scene}\n\n"
        f"Restyle instructions:\n{instruction}\n\n"
        "Keep every main subject, person, vehicle, and the same category. "
        "If the description includes soldiers or military gear, stay military. "
        "If it includes a character, keep the character. "
        "Do not output landscape, cityscape, plaza, or architecture-only scenery "
        "unless that is already the described subject."
    )


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

    def _auth_headers(self) -> dict[str, str]:
        if not self._resolved_key:
            self._resolved_key = resolve_api_key(self.settings, transport=self.transport)
        return {"Authorization": f"Bearer {self._resolved_key}"}

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
        retry_tools_error: bool = False,
    ) -> dict:
        kwargs: dict = {"timeout": self.timeout if timeout is None else timeout}
        if self.transport is not None:
            kwargs["transport"] = self.transport
        last_error: Exception | None = None
        attempts = max(1, retries + 1)
        for attempt in range(attempts):
            if stop_requested():
                raise JobStopped("已手动停止")
            try:
                with httpx.Client(**kwargs) as client:
                    push_http(client)
                    try:
                        response = client.post(
                            self._url(path),
                            headers=self._headers(),
                            json=payload,
                        )
                    finally:
                        pop_http(client)
                return _json_or_error(response)
            except JobStopped:
                raise
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if stop_requested():
                    raise JobStopped("已手动停止") from exc
                last_error = ApiError(f"中转站网络超时或中断：{exc}")
            except ApiError as exc:
                last_error = exc
                retryable = is_transient_relay_error(str(exc))
                if retry_tools_error and _is_tools_choice_error(str(exc)):
                    retryable = True
                if not retryable:
                    raise
            except Exception as exc:
                if stop_requested():
                    raise JobStopped("已手动停止") from exc
                raise
            if attempt + 1 >= attempts:
                break
            wait_or_stop(2 * (attempt + 1))
        assert last_error is not None
        raise last_error

    def _post_multipart(
        self,
        path: str,
        *,
        files: dict,
        data: dict,
        retries: int = 0,
    ) -> dict:
        kwargs: dict = {"timeout": self.timeout}
        if self.transport is not None:
            kwargs["transport"] = self.transport
        last_error: Exception | None = None
        attempts = max(1, retries + 1)
        for attempt in range(attempts):
            if stop_requested():
                raise JobStopped("已手动停止")
            try:
                with httpx.Client(**kwargs) as client:
                    push_http(client)
                    try:
                        response = client.post(
                            self._url(path),
                            headers=self._auth_headers(),
                            data=data,
                            files=files,
                        )
                    finally:
                        pop_http(client)
                return _json_or_error(response)
            except JobStopped:
                raise
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if stop_requested():
                    raise JobStopped("已手动停止") from exc
                last_error = ApiError(f"中转站网络超时或中断：{exc}")
            except ApiError as exc:
                last_error = exc
                if not is_transient_relay_error(str(exc)):
                    raise
            except Exception as exc:
                if stop_requested():
                    raise JobStopped("已手动停止") from exc
                raise
            if attempt + 1 >= attempts:
                break
            wait_or_stop(2 * (attempt + 1))
        assert last_error is not None
        raise last_error

    def resolve_title_model(self) -> str:
        """Pick a chat/vision model. gpt-image-2 cannot write titles."""
        for candidate in (self.settings.filename_model, self.settings.remix_chat_model):
            if chat_model_supports_titles(candidate):
                return candidate.strip()
        return ""

    def generate_title(self, original_stem: str, image: Path | None = None) -> str:
        model = self.resolve_title_model()
        if not model:
            raise ApiError(
                f"文件名模型 {self.settings.filename_model or '空'} 不支持对话接口，无法根据图片写标题。"
            )
        prompt = self.settings.filename_prompt.strip() or "Generate a short wallpaper title."
        user_content: list | str
        if image is not None and image.exists():
            mime = mimetypes.guess_type(image.name)[0] or "image/png"
            encoded = base64.b64encode(image.read_bytes()).decode("ascii")
            data_url = f"data:{mime};base64,{encoded}"
            user_content = [
                {
                    "type": "text",
                    "text": (
                        f"{prompt}\n"
                        "Look at this wallpaper and write one title that follows the instructions above. "
                        f"Original filename: {original_stem}"
                    ),
                },
                {"type": "image_url", "image_url": {"url": data_url}},
            ]
        else:
            user_content = f"{prompt}\nOriginal filename: {original_stem}"
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Follow the title instructions exactly, including the requested language. "
                        "Return only the title text. No quotes, no file extension."
                    ),
                },
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 64,
        }
        data = self._post_json("/v1/chat/completions", payload, timeout=20.0)
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ApiError("文件名接口返回格式无法解析。") from exc
        return sanitize_filename(str(text), fallback=original_stem)

    def remix_image(
        self,
        source: Path,
        dest_dir: Path,
        title: str,
        *,
        allow_fallback: bool = True,
    ) -> Path:
        mime = mimetypes.guess_type(source.name)[0] or "image/png"
        raw = source.read_bytes()
        encoded = base64.b64encode(raw).decode("ascii")
        data_url = f"data:{mime};base64,{encoded}"
        errors: list[str] = []
        _api_size, target = resolve_remix_size(self.settings.image_size)
        prompt = build_remix_prompt(self.settings.remix_prompt)
        image_model = self.settings.remix_model.strip() or "gpt-image-2"
        size = official_image_size(self.settings.image_size)

        def _save(image_bytes: bytes, suffix: str) -> Path:
            if target:
                image_bytes = fit_image_bytes(image_bytes, target, suffix)
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = unique_path(dest_dir, title, suffix)
            dest.write_bytes(image_bytes)
            return dest

        for path, payload in self._remix_requests(data_url, mime):
            try:
                data = self._post_json(path, payload, retries=3)
                image_bytes, suffix = extract_image_payload(data, source.suffix)
            except ApiError as exc:
                errors.append(f"{path}: {exc}")
                continue
            return _save(image_bytes, suffix)

        try:
            data = self._post_multipart(
                "/v1/images/edits",
                files={"image": (source.name, raw, mime)},
                data={"model": image_model, "prompt": prompt, "size": size, "n": "1"},
                retries=1,
            )
            image_bytes, suffix = extract_image_payload(data, source.suffix)
            return _save(image_bytes, suffix)
        except ApiError as exc:
            errors.append(f"/v1/images/edits(multipart): {exc}")

        # newxxt's admin-panel generations test is text-to-image. Extra image
        # fields on that path are either stripped or rewritten to the broken
        # edits/tools channel, so a 200 there would invent scenery. Only generate
        # without the file after a vision pass has named the real subject.
        described = ""
        try:
            described = self._describe_source_for_generation(source)
        except ApiError as exc:
            errors.append(f"/v1/chat/completions(识图): {exc}")
        if described.strip():
            try:
                data = self._post_json(
                    "/v1/images/generations",
                    {
                        "model": image_model,
                        "prompt": described,
                        "size": size,
                        "quality": "medium",
                    },
                    retries=1,
                    retry_tools_error=True,
                )
                image_bytes, suffix = extract_image_payload(data, source.suffix)
                return _save(image_bytes, suffix)
            except ApiError as exc:
                errors.append(f"/v1/images/generations(识图文生图): {exc}")

        if allow_fallback:
            fallback = self._fallback_image_client()
            if fallback is not None:
                try:
                    return fallback.remix_image(source, dest_dir, title, allow_fallback=False)
                except ApiError as exc:
                    errors.append(f"备用生图 aipixapi: {exc}")

        combined = " | ".join(errors) if errors else "未知错误"
        raise ApiError(friendly_error_message(combined))

    def _fallback_image_client(self) -> RelayClient | None:
        if normalize_api_base(self.settings.base_url) == normalize_api_base(AIPIX_API_BASE):
            return None
        return RelayClient(
            self.settings.model_copy(
                update={"base_url": AIPIX_API_BASE, "api_key": AIPIX_API_KEY}
            ),
            timeout=self.timeout,
            transport=self.transport,
        )

    def _remix_requests(self, data_url: str, mime: str) -> list[tuple[str, dict]]:
        prompt = build_remix_prompt(self.settings.remix_prompt)
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
        edits_single = (
            "/v1/images/edits",
            {
                "model": image_model,
                "prompt": prompt,
                "image": data_url,
                "size": size,
            },
        )
        image_attempts = [edits, edits_single]
        if not chat_model_supports_titles(chat_model):
            # gpt-image-2 is not a chat model. Prefer true image edits. Do not
            # call /v1/images/generations here: that path ignores the source
            # photo and turns military/character images into scenery.
            return image_attempts
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
            *image_attempts,
        ]

    def _describe_source_for_generation(self, source: Path) -> str:
        model = self.resolve_title_model() or "gpt-5.4-mini"
        if not chat_model_supports_titles(model):
            model = "gpt-5.4-mini"
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You describe photos so another model can restyle them. "
                        "Return only a factual English description. "
                        "No quotes, no markdown, no explanation."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Describe this photo exactly as it is: who or what is in it, "
                                "clothing, gear, vehicles, and setting. "
                                "If there are soldiers, weapons, aircraft, or tactics, say so. "
                                "If there is a person or anime character, describe them. "
                                "Do not turn it into a generic landscape wallpaper, "
                                "European street, city square, or architecture-only scene "
                                "unless that is literally all the photo contains."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": _vision_data_url(source)}},
                    ],
                },
            ],
            "max_tokens": 400,
        }
        last_error: ApiError | None = None
        for client in self._vision_clients():
            try:
                data = client._post_json("/v1/chat/completions", payload, timeout=40.0)
                text = str(data["choices"][0]["message"]["content"]).strip()
            except (ApiError, KeyError, IndexError, TypeError) as exc:
                last_error = exc if isinstance(exc, ApiError) else ApiError("识图接口返回格式无法解析。")
                continue
            text = text.strip(" \"'`")
            if text:
                return _generation_prompt_from_description(text, self.settings.remix_prompt)
            last_error = ApiError("识图接口没有返回提示词。")
        raise last_error or ApiError("识图失败。")

    def _vision_clients(self) -> list["RelayClient"]:
        clients = [self]
        title = title_api_settings(self.settings)
        if title is not self.settings:
            clients.insert(0, RelayClient(title, timeout=self.timeout, transport=self.transport))
        return clients


def _vision_data_url(source: Path) -> str:
    from io import BytesIO

    from PIL import Image

    with Image.open(source) as image:
        rgb = image.convert("RGB")
        rgb.thumbnail((768, 768))
        buffer = BytesIO()
        rgb.save(buffer, format="JPEG", quality=80)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


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
