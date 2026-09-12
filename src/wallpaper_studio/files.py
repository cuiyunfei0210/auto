from __future__ import annotations

import mimetypes
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
SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "__macosx",
    "二创",
    "output",
    "remixed",
    "remix",
}
UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
MAX_SCAN_DEPTH = 6
MAX_IMAGES = 2000


def _resolved(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return path


def _is_under(path: Path, root: Path) -> bool:
    try:
        _resolved(path).relative_to(_resolved(root))
        return True
    except (OSError, ValueError):
        return False


def list_images(folder: Path, exclude_roots: list[Path] | None = None) -> list[Path]:
    if not folder.exists() or not folder.is_dir():
        return []
    root = _resolved(folder)
    blocked = [_resolved(item) for item in (exclude_roots or []) if item]
    found: list[Path] = []
    seen_paths: set[str] = set()
    seen_fingerprints: set[tuple[str, int]] = set()
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
        resolved = _resolved(path)
        if any(_is_under(resolved, item) for item in blocked):
            continue
        key = str(resolved).lower()
        if key in seen_paths:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            size = -1
        fingerprint = (path.name.lower(), size)
        if fingerprint in seen_fingerprints:
            continue
        seen_paths.add(key)
        seen_fingerprints.add(fingerprint)
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


def clear_images_in_dir(folder: Path) -> int:
    """Delete previously remixed image files so this run's count matches the source."""
    removed = 0
    for path in list_images(folder):
        try:
            path.unlink()
            removed += 1
        except OSError:
            continue
    return removed


def fit_image_bytes(image_bytes: bytes, size: tuple[int, int], suffix: str = ".png") -> bytes:
    """Cover-crop and resize to an exact width/height. Used after gpt-image-2's native sizes."""
    from io import BytesIO

    from PIL import Image

    target_w, target_h = size
    if target_w <= 0 or target_h <= 0:
        return image_bytes
    with Image.open(BytesIO(image_bytes)) as image:
        image = image.convert("RGB")
        if image.size == (target_w, target_h):
            return image_bytes
        src_w, src_h = image.size
        scale = max(target_w / src_w, target_h / src_h)
        resized = image.resize(
            (max(target_w, int(src_w * scale + 0.5)), max(target_h, int(src_h * scale + 0.5))),
            Image.Resampling.LANCZOS,
        )
        left = max(0, (resized.width - target_w) // 2)
        top = max(0, (resized.height - target_h) // 2)
        cropped = resized.crop((left, top, left + target_w, top + target_h))
        buffer = BytesIO()
        fmt = "JPEG" if suffix.lower() in {".jpg", ".jpeg"} else "PNG"
        if fmt == "JPEG":
            cropped.save(buffer, format=fmt, quality=95, subsampling=0)
        else:
            cropped.save(buffer, format=fmt)
        return buffer.getvalue()


MAX_RELAY_SIDE = 1536
MAX_RELAY_BYTES = 1_000_000


def relay_source_payload(path: Path) -> tuple[bytes, str]:
    """Shrink huge camera files before they go to the image-edit API.

    gpt-image-2 only sees ~1536px. Sending a 10MB 4K JPEG as base64 makes the
    relay hang with no log output after 「正在二创」.
    """
    from io import BytesIO

    from PIL import Image

    raw = path.read_bytes()
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    try:
        with Image.open(BytesIO(raw)) as image:
            image.load()
            image = image.convert("RGB")
            width, height = image.size
            if max(width, height) <= MAX_RELAY_SIDE and len(raw) <= MAX_RELAY_BYTES:
                return raw, mime
            scale = min(1.0, MAX_RELAY_SIDE / max(width, height))
            if scale < 1.0:
                image = image.resize(
                    (max(1, int(width * scale)), max(1, int(height * scale))),
                    Image.Resampling.LANCZOS,
                )
            quality = 88
            payload = b""
            while quality >= 50:
                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=quality, optimize=True)
                payload = buffer.getvalue()
                if len(payload) <= MAX_RELAY_BYTES:
                    break
                quality -= 8
            return payload, "image/jpeg"
    except Exception:
        return raw, mime


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
