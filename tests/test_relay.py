from wallpaper_studio.relay import friendly_error_message


def test_friendly_message_for_image_generation_tools_error():
    raw = "Tool choice 'image_generation' not found in 'tools' parameter."
    text = friendly_error_message(raw)
    assert "跳过二创" in text
    assert "中转站生图接口坏了" in text
    assert friendly_error_message(text) == text


def test_friendly_message_for_batch_image_disabled():
    text = friendly_error_message("BATCH_IMAGE_DISABLED")
    assert "跳过二创" in text


def test_friendly_message_keeps_unknown_text():
    assert friendly_error_message("timeout") == "timeout"
    assert friendly_error_message("") == "未知错误"
