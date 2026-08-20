import base64
import json
from pathlib import Path

import httpx

from wallpaper_studio.models import DEFAULT_REMIX_PROMPT, ApiSettings
from wallpaper_studio.relay import (
    RelayClient,
    build_remix_prompt,
    chat_model_supports_titles,
    extract_image_payload,
    friendly_error_message,
    official_image_size,
    resolve_remix_size,
)
from tests.helpers import make_png


def test_friendly_message_for_image_generation_tools_error():
    raw = "Tool choice 'image_generation' not found in 'tools' parameter."
    text = friendly_error_message(raw)
    assert "images/edits" in text
    assert "跳过二创" in text
    assert friendly_error_message(text) == text


def test_friendly_message_for_xbhuiz_image_line():
    text = friendly_error_message("该线路无法完成生图请求,请使用 https://xmapi.site/")
    assert "xmapi.site" in text
    assert "xbhuiz" in text
    assert "gpt-image-2" in text


def test_friendly_message_for_upstream_unavailable():
    text = friendly_error_message("Upstream service temporarily unavailable")
    assert "暂时不可用" in text
    assert "跳过二创" in text
    assert friendly_error_message(text) == text


def test_friendly_message_for_no_compatible_accounts():
    text = friendly_error_message("/v1/images/edits: No available compatible accounts")
    assert "中转站" in text
    assert "跳过二创" in text
    assert friendly_error_message(text) == text


def test_friendly_message_for_batch_image_disabled():
    text = friendly_error_message("BATCH_IMAGE_DISABLED")
    assert "跳过二创" in text


def test_friendly_message_keeps_unknown_text():
    assert friendly_error_message("timeout") == "timeout"
    assert friendly_error_message("") == "未知错误"


def test_official_image_size_maps_1k():
    assert official_image_size("1K") == "1024x1024"
    assert official_image_size("1024x1024") == "1024x1024"
    assert official_image_size("2K") == "1536x1024"
    assert official_image_size("4K") == "1536x1024"


def test_resolve_remix_size_upscales_2k_and_4k():
    assert resolve_remix_size("2K") == ("1536x1024", (2560, 1440))
    assert resolve_remix_size("4K") == ("1536x1024", (3840, 2160))
    assert resolve_remix_size("1920x1080") == ("1536x1024", (1920, 1080))
    assert resolve_remix_size("1536x1024") == ("1536x1024", None)
    assert resolve_remix_size("1K") == ("1024x1024", None)


def test_extract_image_from_responses_payload():
    blob = base64.b64encode(b"fakepng").decode("ascii")
    data = {"output": [{"type": "image_generation_call", "result": blob}]}
    image, suffix = extract_image_payload(data, ".jpg")
    assert image == b"fakepng"
    assert suffix == ".png"


def test_remix_image_model_uses_clean_edits_endpoint(tmp_path: Path):
    source = make_png(tmp_path / "night.png")
    image_b64 = base64.b64encode(source.read_bytes()).decode("ascii")
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        body = json.loads(request.content)
        if request.url.path.endswith("/v1/images/edits"):
            assert body["model"] == "gpt-image-2"
            assert "tools" not in body
            assert body["images"][0]["image_url"].startswith("data:image")
            return httpx.Response(200, json={"data": [{"b64_json": image_b64}]})
        return httpx.Response(
            400,
            json={"error": {"message": "This model is not supported on the Chat Completions endpoint"}},
        )

    client = RelayClient(
        ApiSettings(api_key="sk-test"),
        transport=httpx.MockTransport(handler),
    )
    dest = client.remix_image(source, tmp_path / "out", "星河")
    assert dest.exists()
    assert dest.read_bytes() == source.read_bytes()
    assert seen == ["/v1/images/edits"]


def test_remix_retries_transient_upstream_errors(tmp_path: Path, monkeypatch):
    source = make_png(tmp_path / "night.png")
    image_b64 = base64.b64encode(source.read_bytes()).decode("ascii")
    calls = {"n": 0}
    monkeypatch.setattr("wallpaper_studio.relay.time.sleep", lambda _seconds: None)

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                502,
                json={"error": {"message": "Upstream service temporarily unavailable"}},
            )
        return httpx.Response(200, json={"data": [{"b64_json": image_b64}]})

    client = RelayClient(
        ApiSettings(api_key="sk-test"),
        transport=httpx.MockTransport(handler),
    )
    dest = client.remix_image(source, tmp_path / "out", "星河")
    assert dest.exists()
    assert calls["n"] == 2


def test_remix_chat_model_tries_responses_first(tmp_path: Path):
    source = make_png(tmp_path / "night.png")
    image_b64 = base64.b64encode(source.read_bytes()).decode("ascii")
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        body = json.loads(request.content)
        if request.url.path.endswith("/v1/responses"):
            assert body["model"] == "gpt-4o"
            assert body["tool_choice"] == "auto"
            return httpx.Response(
                200,
                json={"output": [{"type": "image_generation_call", "result": image_b64}]},
            )
        return httpx.Response(400, json={"error": {"message": "nope"}})

    client = RelayClient(
        ApiSettings(api_key="sk-test", remix_chat_model="gpt-4o", remix_model="gpt-image-2"),
        transport=httpx.MockTransport(handler),
    )
    dest = client.remix_image(source, tmp_path / "out", "星河")
    assert dest.exists()
    assert seen[0].endswith("/v1/responses")


def test_remix_falls_back_to_chat_if_responses_has_no_image(tmp_path: Path):
    source = make_png(tmp_path / "night.png")
    image_b64 = base64.b64encode(source.read_bytes()).decode("ascii")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/responses"):
            return httpx.Response(200, json={"output": [{"type": "message", "content": "ok"}]})
        if request.url.path.endswith("/v1/chat/completions"):
            return httpx.Response(
                200,
                json={"choices": [{"message": {"images": [{"b64_json": image_b64}]}}]},
            )
        return httpx.Response(500, json={"error": {"message": "nope"}})

    client = RelayClient(
        ApiSettings(api_key="sk-test", remix_chat_model="gpt-4o"),
        transport=httpx.MockTransport(handler),
    )
    dest = client.remix_image(source, tmp_path / "out", "星河")
    assert dest.exists()
    assert dest.read_bytes() == source.read_bytes()


def test_resolves_api_key_by_logging_into_relay(tmp_path: Path):
    source = make_png(tmp_path / "night.png")
    image_b64 = base64.b64encode(source.read_bytes()).decode("ascii")
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(f"{request.method} {request.url.path}")
        if request.url.path.endswith("/api/v1/auth/login"):
            body = json.loads(request.content)
            assert body["email"] == "596003517@qq.com"
            return httpx.Response(200, json={"code": 0, "data": {"access_token": "jwt-test"}})
        if request.url.path.endswith("/api/v1/keys"):
            assert request.headers["Authorization"] == "Bearer jwt-test"
            return httpx.Response(
                200,
                json={"code": 0, "data": {"items": [{"key": "sk-from-login", "status": "active"}]}},
            )
        if request.url.path.endswith("/v1/images/edits"):
            assert request.headers["Authorization"] == "Bearer sk-from-login"
            return httpx.Response(
                200,
                json={"data": [{"b64_json": image_b64}]},
            )
        return httpx.Response(404, json={"error": {"message": request.url.path}})

    client = RelayClient(
        ApiSettings(api_key="", username="596003517@qq.com", password="123123"),
        transport=httpx.MockTransport(handler),
    )
    dest = client.remix_image(source, tmp_path / "out", "星河")
    assert dest.exists()
    assert any(item.endswith("/api/v1/auth/login") for item in seen)
    assert any(item.endswith("/api/v1/keys") for item in seen)


def test_image_models_are_not_used_for_chat_titles():
    assert chat_model_supports_titles("gpt-4o-mini")
    assert not chat_model_supports_titles("gpt-image-2")
    assert not chat_model_supports_titles("")


def test_empty_remix_prompt_sends_strong_restyle_instruction():
    settings = ApiSettings(remix_prompt="")
    assert settings.remix_prompt == DEFAULT_REMIX_PROMPT
    settings.remix_prompt = "   "
    client = RelayClient(settings)
    path, payload = client._remix_requests("data:image/png;base64,xx", "image/png")[0]
    assert path == "/v1/images/edits"
    assert payload["prompt"].startswith("Primary instruction:")
    assert "禁止原样" in payload["prompt"]
    assert "near-identical" in payload["prompt"]
    assert "Do not default to sunset" in payload["prompt"]
    assert "Restyle this image as a desktop wallpaper." not in payload["prompt"]
    assert "Cinematic lighting" not in payload["prompt"]


def test_custom_remix_prompt_is_primary_and_does_not_force_sunset():
    prompt = build_remix_prompt("把山改成雪景，正午冷色调，不要黄昏。")
    assert "把山改成雪景" in prompt
    assert prompt.startswith("Primary instruction:")
    assert "Do not default to sunset" in prompt


def test_sunset_prompt_skips_anti_dusk_guard():
    prompt = build_remix_prompt("Keep the dolphin, make a dramatic sunset over the ocean.")
    assert "dramatic sunset" in prompt
    assert "Do not default to sunset" not in prompt


def test_do_not_sunset_still_gets_anti_dusk_guard():
    from wallpaper_studio.relay import prompt_asks_for_sunset

    assert prompt_asks_for_sunset("dramatic sunset over the ocean")
    assert not prompt_asks_for_sunset("正午冷色调，不要黄昏")
    assert not prompt_asks_for_sunset("no sunset, use noon light")


def test_remix_upscales_native_2k_canvas(tmp_path: Path):
    from PIL import Image

    source = make_png(tmp_path / "night.png")
    native = tmp_path / "native.png"
    Image.new("RGB", (1536, 1024), (20, 40, 80)).save(native)
    image_b64 = base64.b64encode(native.read_bytes()).decode("ascii")

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["size"] == "1536x1024"
        return httpx.Response(200, json={"data": [{"b64_json": image_b64}]})

    client = RelayClient(
        ApiSettings(api_key="sk-test", image_size="2K"),
        transport=httpx.MockTransport(handler),
    )
    dest = client.remix_image(source, tmp_path / "out", "星河")
    assert dest.exists()
    with Image.open(dest) as image:
        assert image.size == (2560, 1440)
