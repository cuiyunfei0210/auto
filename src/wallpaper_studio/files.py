from __future__ import annotations

import re
from pathlib import Path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def list_images(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    files = [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    ]
    return sorted(files, key=lambda item: item.name.lower())


def sanitize_filename(name: str, fallback: str = "wallpaper") -> str:
    text = (name or "").strip()
    text = text.replace("\n", " ").replace("\r", " ")
    text = UNSAFE_CHARS.sub("", text)
    text = text.strip(" .")
    if text.lower().endswith(tuple(IMAGE_SUFFIXES)):
        text = Path(text).stem
    text = re.sub(r"\s+", " ", text)
    if not text:
        text = fallback
    return text[:80]


def unique_path(directory: Path, stem: str, suffix: str) -> Path:
    candidate = directory / f"{stem}{suffix}"
    index = 2
    while candidate.exists():
        candidate = directory / f"{stem}-{index}{suffix}"
        index += 1
    return candidate


def image_dimensions(path: Path) -> tuple[int, int]:
    from PIL import Image

    with Image.open(path) as image:
        return image.size


def filter_by_min_size(
    images: list[Path],
    min_width: int,
    min_height: int,
) -> tuple[list[Path], list[str]]:
    if min_width <= 0 and min_height <= 0:
        return list(images), []
    kept: list[Path] = []
    skipped: list[str] = []
    for path in images:
        width, height = image_dimensions(path)
        if width < min_width or height < min_height:
            skipped.append(f"{path.name}（{width}x{height}）")
            continue
        kept.append(path)
    return kept, skipped
