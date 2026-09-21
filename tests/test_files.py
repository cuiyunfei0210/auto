from io import BytesIO

from PIL import Image

from wallpaper_studio.files import (
    MAX_RELAY_BYTES,
    MAX_RELAY_SIDE,
    fit_image_bytes,
    image_dimensions,
    relay_source_payload,
)
from tests.helpers import make_png


def test_fit_image_bytes_cover_crops_to_exact_size(tmp_path):
    source = make_png(tmp_path / "small.png")
    raw = source.read_bytes()
    fitted = fit_image_bytes(raw, (1920, 1080), ".png")
    with Image.open(BytesIO(fitted)) as image:
        assert image.size == (1920, 1080)


def test_fit_image_bytes_keeps_matching_size(tmp_path):
    path = tmp_path / "native.png"
    Image.new("RGB", (1536, 1024), (10, 20, 30)).save(path)
    raw = path.read_bytes()
    fitted = fit_image_bytes(raw, (1536, 1024), ".png")
    assert fitted == raw
    assert image_dimensions(path) == (1536, 1024)


def test_relay_source_payload_keeps_small_png(tmp_path):
    source = make_png(tmp_path / "tiny.png")
    raw, mime = relay_source_payload(source)
    assert raw == source.read_bytes()
    assert mime == "image/png"


def test_relay_source_payload_downscales_huge_photo(tmp_path):
    path = tmp_path / "camera.jpg"
    Image.new("RGB", (4000, 3000), (20, 80, 40)).save(path, format="JPEG", quality=95)
    payload, mime = relay_source_payload(path)
    assert mime == "image/jpeg"
    assert len(payload) <= MAX_RELAY_BYTES
    with Image.open(BytesIO(payload)) as image:
        assert max(image.size) <= MAX_RELAY_SIDE
        assert image.size[0] > 0 and image.size[1] > 0
