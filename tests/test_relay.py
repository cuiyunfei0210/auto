import base64
import json
from pathlib import Path

import httpx

from wallpaper_studio.models import DEFAULT_REMIX_PROMPT, ApiSettings
from wallpaper_studio.relay import (
    ApiError,
    RelayClient,
    build_remix_prompt,
    chat_model_supports_titles,
    extract_image_payload,
    friendly_error_message,
    official_image_size,
    parse_model_ids,
    resolve_remix_size,
    sort_title_models,
    title_models_from_payload,
)
from tests.helpers import make_png


def _payload_image_url(body: dict) -> str:
    images = body.get("images") or []
    if images and isinstance(images[0], dict):
        value = images[0].get("image_url")
        if isinstance(value, dict):
            return str(value.get("url") or "")
        if isinstance(value, str):
            return value
    image = body.get("image")
    return str(image or "")


def test_friendly_message_for_invalid_api_key():
    text = friendly_error_message("Invalid API key")
    assert "API Key 无效" in text
    assert friendly_error_message(text) == text
    text = friendly_error_message("Image generation is not enabled for this group")
    assert "对话组" in text
    assert "生图" in text
    assert friendly_error_message(text) == text


def test_friendly_message_for_image_generation_tools_error():
    raw = "Tool choice 'image_generation' not found in 'tools' parameter."
    text = friendly_error_message(raw)
    assert "改图" in text
    assert "文生图" in text
    assert "跳过二创" in text
    assert "aipixapi" not in text.lower()
    assert friendly_error_message(text) == text


def test_friendly_message_collapses_concatenated_copyright_dump():
    raw = (
        "/v1/images/edits: The generated image may violate third-party content similarity protection. | "
        "/v1/images/edits: images[].image_url is required | "
        "/v1/images/generations(识图文生图): 请上传原图 you want to use as a reference. "
        "CATEGORY: 动漫 SUBJECT: Zootopia anime character group size 1536x1024 quality medium | "
        "备用生图 aipixapi: The generated image may violate third-party content similarity protection."
    )
    text = friendly_error_message(raw)
    assert "拦截" in text
    assert "版权" in text
    assert "aipixapi" not in text.lower()
    assert "image_url" not in text
    assert "请上传" not in text
    assert "Zootopia" not in text
    assert "|" not in text
    assert len(text) < 80


def test_friendly_message_for_other_relay_host():
    text = friendly_error_message("该线路无法完成生图请求,请使用 https://xmapi.site/")
    assert "newxxt.top" in text
    assert "gpt-image-2" in text


def test_friendly_message_for_upstream_unavailable():
    text = friendly_error_message("Upstream service temporarily unavailable")
    assert "暂时不可用" in text
    assert "跳过二创" in text
    assert friendly_error_message(text) == text


def test_friendly_message_for_no_compatible_accounts():
    text = friendly_error_message("/v1/images/edits: No available compatible accounts")
    assert "生图 Key" in text
    assert "gpt-image-2" in text
    assert "跳过二创" in text
    assert "/v1/" not in text
    already = "/v1/images/edits: 中转站没有可用的生图线路。请检查额度，或改用「跳过二创」。"
    assert friendly_error_message(already).startswith("生图 Key")
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


def test_resolve_remix_size_upscales_wallpaper_sizes():
    assert resolve_remix_size("2K") == ("1536x1024", (2560, 1440))
    assert resolve_remix_size("4K") == ("1536x1024", (3840, 2160))
    assert resolve_remix_size("1920x1080") == ("1536x1024", (1920, 1080))
    assert resolve_remix_size("1080x1920") == ("1024x1536", (1080, 1920))
    assert resolve_remix_size("1536x1024") == ("1536x1024", None)
    assert resolve_remix_size("1K") == ("1024x1024", None)
    assert resolve_remix_size("2000x1100") == ("1536x1024", (2000, 1100))


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
            url = body["images"][0]["image_url"]
            assert isinstance(url, dict)
            assert url["url"].startswith("data:image")
            return httpx.Response(200, json={"data": [{"b64_json": image_b64}]})
        return httpx.Response(
            400,
            json={"error": {"message": "This model is not supported on the Chat Completions endpoint"}},
        )

    client = RelayClient(
        ApiSettings(api_key="sk-test", image_size="1024x1024"),
        transport=httpx.MockTransport(handler),
    )
    dest = client.remix_image(source, tmp_path / "out", "星河")
    assert dest.exists()
    assert dest.read_bytes() == source.read_bytes()
    image_paths = [item for item in seen if "/v1/images/" in item]
    assert image_paths[0].endswith("/v1/images/edits")
    assert seen.count("/v1/images/generations") == 0


def test_remix_does_not_treat_panel_generations_as_image_edit(tmp_path: Path):
    source = make_png(tmp_path / "night.png")
    image_b64 = base64.b64encode(source.read_bytes()).decode("ascii")
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if request.url.path.endswith("/v1/images/generations"):
            return httpx.Response(200, json={"data": [{"b64_json": image_b64}]})
        if request.url.path.endswith("/v1/images/edits"):
            body = json.loads(request.content)
            assert body["model"] == "gpt-image-2"
            assert _payload_image_url(body).startswith("data:image")
            return httpx.Response(200, json={"data": [{"b64_json": image_b64}]})
        return httpx.Response(
            400,
            json={"error": {"message": "Tool choice 'image_generation' not found in 'tools' parameter."}},
        )

    client = RelayClient(
        ApiSettings(api_key="sk-test", image_size="1024x1024"),
        transport=httpx.MockTransport(handler),
    )
    dest = client.remix_image(source, tmp_path / "out", "星河")
    assert dest.exists()
    image_paths = [item for item in seen if "/v1/images/" in item]
    assert image_paths[0].endswith("/v1/images/edits")
    assert "/v1/images/generations" not in seen


def test_remix_falls_back_to_described_text_to_image(tmp_path: Path):
    source = make_png(tmp_path / "night.png")
    image_b64 = base64.b64encode(source.read_bytes()).decode("ascii")
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        content_type = request.headers.get("content-type", "")
        if content_type.startswith("multipart/"):
            seen.append(f"{request.url.path}:multipart")
            return httpx.Response(
                400,
                json={"error": {"message": "Tool choice 'image_generation' not found in 'tools' parameter."}},
            )
        body = json.loads(request.content)
        seen.append(request.url.path)
        if request.url.path.endswith("/v1/chat/completions"):
            assert any(
                isinstance(item, dict) and item.get("type") == "image_url"
                for item in body["messages"][1]["content"]
            )
            vision_text = body["messages"][1]["content"][0]["text"]
            system = body["messages"][0]["content"]
            assert "军事" in vision_text or "Soldiers" in vision_text or "soldiers" in vision_text
            assert "franchises" in (system + vision_text).lower()
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": "CATEGORY: 军事\nSUBJECT: modern soldier in tactical gear with a rifle"
                            }
                        }
                    ]
                },
            )
        if request.url.path.endswith("/v1/images/generations"):
            if "image" in body or "images" in body:
                return httpx.Response(
                    400,
                    json={"error": {"message": "Tool choice 'image_generation' not found in 'tools' parameter."}},
                )
            assert "modern soldier in tactical gear" in body["prompt"]
            assert "User remix prompt (must follow)" in body["prompt"]
            assert "军事" in body["prompt"]
            assert body.get("quality") == "medium"
            assert "image" not in body
            return httpx.Response(200, json={"data": [{"b64_json": image_b64}]})
        return httpx.Response(
            400,
            json={"error": {"message": "Tool choice 'image_generation' not found in 'tools' parameter."}},
        )

    client = RelayClient(
        ApiSettings(api_key="sk-test", filename_model="gpt-5.4-mini", image_size="1024x1024"),
        transport=httpx.MockTransport(handler),
    )
    dest = client.remix_image(source, tmp_path / "out", "星河")
    assert dest.exists()
    assert dest.read_bytes() == source.read_bytes()
    assert "/v1/chat/completions" in seen
    assert seen.count("/v1/images/generations") >= 2


def test_remix_requests_nested_image_url_before_string_form():
    client = RelayClient(ApiSettings(api_key="sk-test", image_size="1024x1024"))
    edits = [
        payload
        for path, payload in client._remix_requests("data:image/png;base64,xx", "image/png")
        if path.endswith("/v1/images/edits")
    ]
    assert isinstance(edits[0]["images"][0]["image_url"], dict)
    assert edits[0]["images"][0]["image_url"]["url"].startswith("data:image")
    assert isinstance(edits[1]["images"][0]["image_url"], str)
    assert edits[1]["images"][0]["image_url"].startswith("data:image")
    assert "image" in edits[2]
    assert "images" not in edits[2]


def test_remix_tries_generations_with_original_image(tmp_path: Path):
    source = make_png(tmp_path / "night.png")
    image_b64 = base64.b64encode(source.read_bytes()).decode("ascii")
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        content_type = request.headers.get("content-type", "")
        if content_type.startswith("multipart/"):
            seen.append("edits:multipart")
            return httpx.Response(
                400,
                json={"error": {"message": "images[].image_url is required"}},
            )
        body = json.loads(request.content)
        seen.append(request.url.path)
        if request.url.path.endswith("/v1/images/generations"):
            url = _payload_image_url(body)
            assert url.startswith("data:image")
            assert isinstance(body["images"][0]["image_url"], dict)
            return httpx.Response(200, json={"data": [{"b64_json": image_b64}]})
        return httpx.Response(
            400,
            json={"error": {"message": "images[].image_url is required"}},
        )

    client = RelayClient(
        ApiSettings(api_key="sk-test", image_size="1024x1024"),
        transport=httpx.MockTransport(handler),
    )
    dest = client.remix_image(source, tmp_path / "out", "星河")
    assert dest.exists()
    assert "/v1/images/generations" in seen
    assert any(item.endswith("/v1/images/edits") for item in seen)


def test_remix_copyright_block_skips_resending_original(tmp_path: Path):
    source = make_png(tmp_path / "night.png")
    image_b64 = base64.b64encode(source.read_bytes()).decode("ascii")
    generations_with_file = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers.get("content-type", "").startswith("multipart/"):
            raise AssertionError("copyright block should not retry multipart original")
        body = json.loads(request.content)
        if request.url.path.endswith("/v1/chat/completions"):
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    "CATEGORY: 动漫\n"
                                    "SUBJECT: orange fox in a police uniform standing beside a gray rabbit"
                                )
                            }
                        }
                    ]
                },
            )
        if request.url.path.endswith("/v1/images/edits"):
            return httpx.Response(
                400,
                json={
                    "error": {
                        "message": "The generated image may violate third-party content similarity protection."
                    }
                },
            )
        if request.url.path.endswith("/v1/images/generations"):
            if "image" in body or "images" in body:
                generations_with_file["n"] += 1
                return httpx.Response(
                    400,
                    json={
                        "error": {
                            "message": "The generated image may violate third-party content similarity protection."
                        }
                    },
                )
            assert "orange fox in a police uniform" in body["prompt"]
            assert "Zootopia" not in body["prompt"]
            return httpx.Response(200, json={"data": [{"b64_json": image_b64}]})
        return httpx.Response(400, json={"error": {"message": "nope"}})

    client = RelayClient(
        ApiSettings(api_key="sk-test", filename_model="gpt-5.4-mini", image_size="1024x1024"),
        transport=httpx.MockTransport(handler),
    )
    dest = client.remix_image(source, tmp_path / "out", "星河")
    assert dest.exists()
    assert generations_with_file["n"] == 0


def test_remix_does_not_silently_text_to_image_when_vision_fails(tmp_path: Path, monkeypatch):
    source = make_png(tmp_path / "night.png")
    image_b64 = base64.b64encode(source.read_bytes()).decode("ascii")
    monkeypatch.setattr("wallpaper_studio.relay.wait_or_stop", lambda _seconds: None)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers.get("content-type", "").startswith("multipart/"):
            return httpx.Response(
                400,
                json={"error": {"message": "Tool choice 'image_generation' not found in 'tools' parameter."}},
            )
        body = json.loads(request.content) if request.content else {}
        if request.url.path.endswith("/v1/images/generations") and "image" not in body and "images" not in body:
            return httpx.Response(200, json={"data": [{"b64_json": image_b64}]})
        return httpx.Response(
            400,
            json={"error": {"message": "Tool choice 'image_generation' not found in 'tools' parameter."}},
        )

    client = RelayClient(
        ApiSettings(api_key="sk-test", image_size="1024x1024"),
        transport=httpx.MockTransport(handler),
    )
    try:
        client.remix_image(source, tmp_path / "out", "星河")
    except ApiError as exc:
        text = str(exc)
    else:
        raise AssertionError("prompt-only generations must not count as remix")
    assert "识图" in text or "改图" in text


def test_remix_does_not_call_another_relay_when_newxxt_fails(tmp_path: Path, monkeypatch):
    source = make_png(tmp_path / "night.png")
    seen: list[str] = []
    monkeypatch.setattr("wallpaper_studio.relay.wait_or_stop", lambda _seconds: None)

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(
            400,
            json={"error": {"message": "Tool choice 'image_generation' not found in 'tools' parameter."}},
        )

    client = RelayClient(
        ApiSettings(base_url="https://api.newxxt.top", api_key="sk-newxxt", image_size="1024x1024"),
        transport=httpx.MockTransport(handler),
    )
    try:
        client.remix_image(source, tmp_path / "out", "星河")
    except ApiError as exc:
        text = str(exc)
    else:
        raise AssertionError("expected remix to fail without a second relay")
    assert all("aipixapi" not in url and "xmapi" not in url for url in seen)
    assert "改图" in text or "跳过二创" in text


def test_remix_falls_back_to_multipart_edits(tmp_path: Path):
    source = make_png(tmp_path / "night.png")
    image_b64 = base64.b64encode(source.read_bytes()).decode("ascii")
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        content_type = request.headers.get("content-type", "")
        kind = "multipart" if content_type.startswith("multipart/") else "json"
        seen.append(f"{request.url.path}:{kind}")
        if request.url.path.endswith("/v1/images/edits") and kind == "multipart":
            return httpx.Response(200, json={"data": [{"b64_json": image_b64}]})
        return httpx.Response(
            400,
            json={"error": {"message": "Tool choice 'image_generation' not found in 'tools' parameter."}},
        )

    client = RelayClient(
        ApiSettings(api_key="sk-test", image_size="1024x1024"),
        transport=httpx.MockTransport(handler),
    )
    dest = client.remix_image(source, tmp_path / "out", "星河")
    assert dest.exists()
    assert "/v1/images/edits:json" in seen
    assert "/v1/images/edits:multipart" in seen
    assert "/v1/images/generations:json" not in seen


def test_remix_explains_that_panel_text_to_image_is_not_edits(tmp_path: Path, monkeypatch):
    source = make_png(tmp_path / "night.png")
    monkeypatch.setattr("wallpaper_studio.relay.wait_or_stop", lambda _seconds: None)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": {"message": "Tool choice 'image_generation' not found in 'tools' parameter."}},
        )

    client = RelayClient(
        ApiSettings(api_key="sk-test", image_size="1024x1024"),
        transport=httpx.MockTransport(handler),
    )
    try:
        client.remix_image(source, tmp_path / "out", "星河")
    except ApiError as exc:
        text = str(exc)
    else:
        raise AssertionError("expected remix to fail")
    assert "文生图" in text
    assert "改图" in text
    assert "跳过二创" in text
    assert "aipixapi" not in text.lower()


def test_remix_retries_transient_upstream_errors(tmp_path: Path, monkeypatch):
    source = make_png(tmp_path / "night.png")
    image_b64 = base64.b64encode(source.read_bytes()).decode("ascii")
    calls = {"n": 0}
    monkeypatch.setattr("wallpaper_studio.relay.wait_or_stop", lambda _seconds: None)

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                502,
                json={"error": {"message": "Upstream service temporarily unavailable"}},
            )
        return httpx.Response(200, json={"data": [{"b64_json": image_b64}]})

    client = RelayClient(
        ApiSettings(api_key="sk-test", image_size="1024x1024"),
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
        ApiSettings(
            api_key="sk-test",
            remix_chat_model="gpt-4o",
            remix_model="gpt-image-2",
            image_size="1024x1024",
        ),
        transport=httpx.MockTransport(handler),
    )
    dest = client.remix_image(source, tmp_path / "out", "星河")
    assert dest.exists()
    assert "/v1/responses" in seen


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
        ApiSettings(api_key="sk-test", remix_chat_model="gpt-4o", image_size="1024x1024"),
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
        ApiSettings(
            api_key="",
            username="596003517@qq.com",
            password="123123",
            image_size="1024x1024",
        ),
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
    assert payload["prompt"].startswith("Primary instruction")
    assert "user remix prompt, must follow" in payload["prompt"]
    assert "禁止原样" in payload["prompt"]
    assert "Keep the source photo's CQwall category" in payload["prompt"]
    assert "Never turn people or military" in payload["prompt"]
    assert "Do not default to sunset" in payload["prompt"]
    assert "Restyle this image as a desktop wallpaper." not in payload["prompt"]
    assert "Cinematic lighting" not in payload["prompt"]


def test_custom_remix_prompt_is_primary_and_does_not_force_sunset():
    prompt = build_remix_prompt("把山改成雪景，正午冷色调，不要黄昏。")
    assert "把山改成雪景" in prompt
    assert prompt.startswith("Primary instruction")
    assert "user remix prompt, must follow" in prompt
    assert "Do not default to sunset" in prompt
    assert "Never turn people or military" in prompt


def test_user_copy_prompt_is_kept_and_category_is_locked():
    prompt = build_remix_prompt(
        "参考这张图，直接把原图做出来。Refer to this image and directly create the original image.",
        category="军事",
    )
    assert "直接把原图做出来" in prompt
    assert "directly create the original image" in prompt
    assert "Source category is 军事" in prompt
    assert "must follow" in prompt


def test_remix_locked_category_ignores_vision_label(tmp_path: Path):
    source = make_png(tmp_path / "night.png")
    image_b64 = base64.b64encode(source.read_bytes()).decode("ascii")
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if request.url.path.endswith("/v1/chat/completions"):
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "CATEGORY: 风景\nSUBJECT: a lake"}}]},
            )
        body = json.loads(request.content)
        assert "Source category is 军事" in body["prompt"]
        assert "Keep the source photo's CQwall category" not in body["prompt"]
        return httpx.Response(200, json={"data": [{"b64_json": image_b64}]})

    client = RelayClient(
        ApiSettings(api_key="sk-test", image_size="1024x1024"),
        transport=httpx.MockTransport(handler),
    )
    dest = client.remix_image(source, tmp_path / "out", "星河", category="军事")
    assert dest.exists()
    assert client.last_source_category == "军事"
    assert all("/v1/chat/completions" not in path for path in seen)


def test_sunset_prompt_skips_anti_dusk_guard():
    prompt = build_remix_prompt("Keep the dolphin, make a dramatic sunset over the ocean.")
    assert "dramatic sunset" in prompt
    assert "Do not default to sunset" not in prompt


def test_do_not_sunset_still_gets_anti_dusk_guard():
    from wallpaper_studio.relay import prompt_asks_for_sunset

    assert prompt_asks_for_sunset("dramatic sunset over the ocean")
    assert not prompt_asks_for_sunset("正午冷色调，不要黄昏")
    assert not prompt_asks_for_sunset("no sunset, use noon light")


def test_remix_upscales_when_user_asks_2k(tmp_path: Path):
    from PIL import Image

    source = make_png(tmp_path / "night.png")
    native = tmp_path / "native.png"
    Image.new("RGB", (1536, 1024), (20, 40, 80)).save(native)
    image_b64 = base64.b64encode(native.read_bytes()).decode("ascii")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/chat/completions"):
            return httpx.Response(400, json={"error": {"message": "nope"}})
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


def test_remix_upscales_1920x1080(tmp_path: Path):
    from PIL import Image

    source = make_png(tmp_path / "night.png")
    native = tmp_path / "native.png"
    Image.new("RGB", (1536, 1024), (20, 40, 80)).save(native)
    image_b64 = base64.b64encode(native.read_bytes()).decode("ascii")

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"b64_json": image_b64}]})

    client = RelayClient(
        ApiSettings(api_key="sk-test", image_size="1920x1080"),
        transport=httpx.MockTransport(handler),
    )
    dest = client.remix_image(source, tmp_path / "out", "星河")
    with Image.open(dest) as image:
        assert image.size == (1920, 1080)


def test_title_api_settings_can_use_a_second_key():
    from wallpaper_studio.models import ApiSettings, title_api_settings

    settings = ApiSettings(
        base_url="https://api.newxxt.top",
        api_key="sk-image",
        filename_model="gpt-5.4-mini",
        filename_base_url="https://api.newxxt.top",
        filename_api_key="sk-chat",
    )
    title = title_api_settings(settings)
    assert title.base_url == "https://api.newxxt.top"
    assert title.api_key == "sk-chat"
    assert title_api_settings(ApiSettings(base_url="https://api.newxxt.top", api_key="sk-same")).api_key == "sk-same"


def test_title_api_settings_skips_dead_builtin_chat_key():
    from wallpaper_studio.models import NEWXXT_CHAT_KEY, title_api_settings, title_list_key_candidates

    settings = ApiSettings(
        base_url="https://api.newxxt.top",
        api_key="sk-live-image",
        filename_api_key=NEWXXT_CHAT_KEY,
    )
    assert title_api_settings(settings).api_key == "sk-live-image"
    assert title_list_key_candidates(settings) == ["sk-live-image"]
    assert title_list_key_candidates(ApiSettings(api_key=NEWXXT_CHAT_KEY, filename_api_key=NEWXXT_CHAT_KEY)) == []


def test_generate_title_uses_filename_relay_host(tmp_path: Path):
    source = make_png(tmp_path / "night.png")
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        assert request.headers["Authorization"] == "Bearer sk-chat"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "红旗街景"}}]},
        )

    from wallpaper_studio.models import title_api_settings

    settings = ApiSettings(
        api_key="sk-image",
        base_url="https://api.newxxt.top",
        filename_model="gpt-5.4-mini",
        filename_base_url="https://api.newxxt.top",
        filename_api_key="sk-chat",
    )
    client = RelayClient(title_api_settings(settings), transport=httpx.MockTransport(handler))
    assert client.generate_title("night", source) == "红旗街景"
    assert seen and "chat/completions" in seen[0]


def test_friendly_message_for_missing_chat_model():
    text = friendly_error_message('Model "gpt-5.4-mini" is not supported by any configured account in this group')
    assert "newxxt" in text
    assert "gpt-image-2" in text


def test_generate_title_sends_the_image(tmp_path: Path):
    source = make_png(tmp_path / "night.png")
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "红旗街景"}}]},
        )

    client = RelayClient(
        ApiSettings(api_key="sk-test", filename_model="gpt-4o-mini"),
        transport=httpx.MockTransport(handler),
    )
    title = client.generate_title("night", source)
    assert title == "红旗街景"
    content = seen[0]["messages"][1]["content"]
    assert isinstance(content, list)
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image")
    text = content[0]["text"]
    assert "Chinese title" not in text
    assert "Write a short English wallpaper title" in text
    system = seen[0]["messages"][0]["content"]
    assert "requested language" in system


def test_generate_title_keeps_english_prompt(tmp_path: Path):
    source = make_png(tmp_path / "night.png")
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Red Flag Street"}}]},
        )

    client = RelayClient(
        ApiSettings(
            api_key="sk-test",
            filename_model="gpt-4o-mini",
            filename_prompt="生成简短英文壁纸标题，最多 18 字符，不带文件后缀与引号。",
        ),
        transport=httpx.MockTransport(handler),
    )
    assert client.generate_title("night", source) == "Red Flag Street"
    text = seen[0]["messages"][1]["content"][0]["text"]
    assert "生成简短英文壁纸标题" in text
    assert "Chinese" not in text
    assert "中文" not in seen[0]["messages"][0]["content"]


def test_resolve_title_model_skips_image_models():
    client = RelayClient(ApiSettings(filename_model="gpt-image-2", remix_chat_model="gpt-image-2"))
    assert client.resolve_title_model() == ""
    client = RelayClient(ApiSettings(filename_model="gpt-image-2", remix_chat_model="gpt-4o-mini"))
    assert client.resolve_title_model() == "gpt-4o-mini"


def test_parse_model_ids_accepts_openai_and_newapi_shapes():
    openai_ids = parse_model_ids(
        {
            "object": "list",
            "data": [
                {"id": "gpt-5.4-mini"},
                {"id": "gpt-5.4"},
                {"id": "gpt-image-2"},
            ],
        }
    )
    assert openai_ids == ["gpt-5.4-mini", "gpt-5.4", "gpt-image-2"]
    assert parse_model_ids({"data": ["gpt-5.4", "gpt-4o-mini"]}) == ["gpt-5.4", "gpt-4o-mini"]
    assert parse_model_ids({"data": {"models": [{"name": "gpt-5.2"}]}}) == ["gpt-5.2"]


def test_title_models_from_payload_drops_image_models_and_sorts():
    models = title_models_from_payload(
        {
            "data": [
                {"id": "gpt-4o"},
                {"id": "gpt-image-2"},
                {"id": "dall-e-3"},
                {"id": "gpt-5.4"},
                {"id": "gpt-5.4-mini"},
            ]
        }
    )
    assert models == ["gpt-5.4-mini", "gpt-5.4", "gpt-4o"]
    assert "gpt-image-2" not in models
    assert sort_title_models(["gpt-4o", "gpt-5.4-mini"]) == ["gpt-5.4-mini", "gpt-4o"]


def test_list_title_models_uses_relay_models_endpoint():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        assert request.method == "GET"
        return httpx.Response(
            200,
            json={
                "object": "list",
                "data": [
                    {"id": "gpt-5.4-mini"},
                    {"id": "gpt-5.4"},
                    {"id": "gpt-image-2"},
                    {"id": "claude-sonnet-4.6"},
                ],
            },
        )

    client = RelayClient(ApiSettings(api_key="sk-test"), transport=httpx.MockTransport(handler))
    assert client.list_title_models() == ["gpt-5.4-mini", "gpt-5.4", "claude-sonnet-4.6"]
    assert any("/v1/models" in url for url in seen)


def test_list_title_models_rejects_invalid_key_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": "INVALID_API_KEY", "message": "Invalid API key"})

    client = RelayClient(ApiSettings(api_key="sk-bad"), transport=httpx.MockTransport(handler))
    try:
        client.list_title_models()
    except ApiError as exc:
        assert "Invalid API key" in str(exc)
    else:
        raise AssertionError("expected invalid key to fail")


def test_remix_shrinks_camera_jpeg_before_relay(tmp_path: Path):
    from PIL import Image

    from wallpaper_studio.files import MAX_RELAY_BYTES, MAX_RELAY_SIDE

    source = tmp_path / "camera.jpg"
    Image.new("RGB", (4000, 3000), (20, 40, 60)).save(source, format="JPEG", quality=95)
    sent: dict[str, object] = {}
    tiny = make_png(tmp_path / "tiny.png").read_bytes()
    tiny_b64 = base64.b64encode(tiny).decode("ascii")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/images/edits"):
            body = json.loads(request.content)
            url = body["images"][0]["image_url"]["url"]
            header, encoded = url.split(",", 1)
            raw = base64.b64decode(encoded)
            sent["bytes"] = len(raw)
            sent["header"] = header
            (tmp_path / "sent.jpg").write_bytes(raw)
            return httpx.Response(200, json={"data": [{"b64_json": tiny_b64}]})
        return httpx.Response(400, json={"error": {"message": "skip"}})

    logs: list[str] = []
    client = RelayClient(
        ApiSettings(api_key="sk-test", image_size="1024x1024"),
        transport=httpx.MockTransport(handler),
        log=logs.append,
    )
    dest = client.remix_image(source, tmp_path / "out", "山峰")
    assert dest.exists()
    assert sent["bytes"] <= MAX_RELAY_BYTES
    assert "image/jpeg" in str(sent["header"])
    with Image.open(tmp_path / "sent.jpg") as image:
        assert max(image.size) <= MAX_RELAY_SIDE
    assert any("压缩" in line for line in logs)
    assert any("/v1/images/edits" in line for line in logs)


def test_in_flight_heartbeat_keeps_writing_logs():
    import time

    logs: list[str] = []
    client = RelayClient(ApiSettings(api_key="sk-test"), log=logs.append)
    with client._in_flight("正在请求中转站 /v1/images/edits…", interval=0.08):
        time.sleep(0.22)
    assert logs[0] == "正在请求中转站 /v1/images/edits…"
    assert any("已等待" in line for line in logs[1:])
