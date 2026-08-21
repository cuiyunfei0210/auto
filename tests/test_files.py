from io import BytesIO

from PIL import Image

from wallpaper_studio.files import fit_image_bytes, image_dimensions
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
