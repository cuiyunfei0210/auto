from __future__ import annotations

import re
from pathlib import Path

IMAGE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".jpe",
    ".jfif",
    ".webp",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
    ".heic",
    ".heif",
}
SKIP_DIR_NAMES = {".git", "__pycache__", "node_modules", ".venv", "__macosx"}
UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
MAX_SCAN_DEPTH = 6
MAX_IMAGES = 2000


def list_images(folder: Path) -> list[Path]:
    if not folder.exists() or not folder.is_dir():
        return []
    root = folder
    try:
        root = folder.resolve()
    except OSError:
        root = folder
    found: list[Path] = []
    scanned = 0
    try:
        iterator = root.rglob("*")
    except OSError:
        return []
    for path in iterator:
        scanned += 1
        if scanned > 20000:
            break
        try:
            if not path.is_file():
                continue
            rel = path.relative_to(root)
        except OSError:
            continue
        except ValueError:
            continue
        if len(rel.parts) - 1 > MAX_SCAN_DEPTH:
            continue
        if any(part.startswith(".") or part.lower() in SKIP_DIR_NAMES for part in rel.parts[:-1]):
            continue
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        found.append(path)
        if len(found) >= MAX_IMAGES:
            break
    return sorted(found, key=lambda item: str(item).lower())


def empty_source_message(folder: Path) -> str:
    folder = Path(folder)
    if not folder.exists():
        return (
            f"源文件夹不存在：{folder}。"
            "请到「文件夹」填一个存在的目录，或把图片放到程序旁边的 data\\source。"
        )
    if not folder.is_dir():
        return f"源路径不是文件夹：{folder}。"
    try:
        entries = list(folder.iterdir())
    except OSError as exc:
        return f"无法读取源文件夹 {folder}：{exc}"
    parts = [f"源文件夹里没有图片：{folder}。"]
    files = [path for path in entries if path.is_file()]
    dirs = [path for path in entries if path.is_dir()]
    if not entries:
        parts.append(
            "这个目录现在是空的。请把 png/jpg/webp 复制进去，不要只放在桌面或 WallpaperStudio 根目录。"
        )
        return "".join(parts)
    if files:
        shown = "、".join(path.name for path in files[:8])
        suffixes = sorted({(path.suffix.lower() or "无扩展名") for path in files})
        parts.append(f"根目录现有文件：{shown}。扩展名：{'、'.join(suffixes)}。")
        if any(path.suffix.lower() == ".lnk" for path in files):
            parts.append("快捷方式不算，请放入图片文件本身。")
        else:
            parts.append("目前认 png/jpg/jpeg/webp/bmp/gif/jfif/tif。")
    if dirs:
        shown = "、".join(path.name for path in dirs[:6])
        parts.append(f"里面有子文件夹：{shown}。程序会往下找，但这些子文件夹里也没有图片。")
    return "".join(parts)


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
