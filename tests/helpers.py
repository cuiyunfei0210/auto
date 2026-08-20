from pathlib import Path

from PIL import Image


def make_png(path: Path, color: tuple[int, int, int] = (200, 40, 40)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), color).save(path)
    return path
