import base64
import json
from pathlib import Path

import httpx

from wallpaper_studio.models import ApiSettings
from wallpaper_studio.relay import (
    RelayClient,
    extract_image_payload,
    friendly_error_message,
    official_image_size,
)
from tests.helpers import make_png


def test_friendly_message_for_image_generation_tools_error():
    raw = "Tool choice 'image_generation' not found in 'tools' parameter."
    text = friendly_error_message(raw)
    assert "responses" in text
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


def test_extract_image_from_responses_payload():
    blob = base64.b64encode(b"fakepng").decode("ascii")
    data = {"output": [{"type": "image_generation_call", "result": blob}]}
    image, suffix = extract_image_payload(data, ".jpg")
    assert image == b"fakepng"
    assert suffix == ".png"


def test_remix_uses_responses_instead_of_broken_images_endpoint(tmp_path: Path):
    source = make_png(tmp_path / "night.png")
    image_b64 = base64.b64encode(source.read_bytes()).decode("ascii")
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        body = json.loads(request.content)
        if request.url.path.endswith("/v1/responses"):
            assert body["model"] == "gpt-image-2"
            assert body["tool_choice"] == "auto"
            assert body["tools"][0]["type"] == "image_generation"
            assert any(
                part.get("type") == "input_image"
                for part in body["input"][0]["content"]
            )
            return httpx.Response(
                200,
                json={"output": [{"type": "image_generation_call", "result": image_b64}]},
            )
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": "Tool choice 'image_generation' not found in 'tools' parameter."
                }
            },
        )

    client = RelayClient(
        ApiSettings(api_key="sk-test"),
        transport=httpx.MockTransport(handler),
    )
    dest = client.remix_image(source, tmp_path / "out", "星河")
    assert dest.exists()
    assert dest.read_bytes() == source.read_bytes()
    assert seen[0].endswith("/v1/responses")
    assert not any(path.endswith("/v1/images/edits") for path in seen)


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
        ApiSettings(api_key="sk-test"),
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
        if request.url.path.endswith("/v1/responses"):
            assert request.headers["Authorization"] == "Bearer sk-from-login"
            return httpx.Response(
                200,
                json={"output": [{"type": "image_generation_call", "result": image_b64}]},
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
