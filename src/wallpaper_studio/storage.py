from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import ValidationError

from wallpaper_studio.models import AppConfig, apply_builtin_defaults, effective_remix_prompt
from wallpaper_studio.paths import app_root

DEFAULT_PORT = 8765
CONFIG_FILENAME = "config.json"
_PUBLIC_USER_DIRS = {"public", "default", "all users", "default user"}


def _path_tokens(path: Path | str) -> list[str]:
    return [part for part in str(path).replace("\\", "/").split("/") if part and part != "."]


def current_username() -> str:
    return (os.environ.get("USERNAME") or os.environ.get("USER") or "").strip()


def is_foreign_user_path(path: Path | str) -> bool:
    """True when an absolute path belongs to another Windows/macOS user profile."""
    tokens = [part.lower() for part in _path_tokens(path)]
    current = current_username().lower()
    if not current:
        return False
    for marker in ("users", "documents and settings"):
        if marker not in tokens:
            continue
        index = tokens.index(marker)
        if index + 1 >= len(tokens):
            return False
        owner = tokens[index + 1]
        if owner in _PUBLIC_USER_DIRS:
            return False
        return owner != current
    return False


def _writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".writeok"
        probe.write_text("1", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def data_dir() -> Path:
    raw = os.environ.get("WALLPAPER_STUDIO_HOME")
    candidates: list[Path] = []
    if raw:
        candidates.append(Path(raw).expanduser())
    else:
        candidates.append(app_root() / "data")
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidates.append(Path(appdata) / "WallpaperStudio")
        candidates.append(Path.home() / "WallpaperStudio")
    for path in candidates:
        if _writable_dir(path):
            return path
    raise OSError("无法创建数据目录，请把整个 WallpaperStudio 文件夹拷到桌面或 D 盘后再打开。")


def config_path() -> Path:
    return data_dir() / CONFIG_FILENAME


def _try_save(config: AppConfig) -> None:
    try:
        save_config(config)
    except OSError:
        pass


def resolve_work_dir(configured: str, fallback: Path) -> tuple[Path, str]:
    """Pick a usable folder. Never raise; ignore other PCs' user paths."""
    if not _writable_dir(fallback):
        fallback = data_dir() / fallback.name
        fallback.mkdir(parents=True, exist_ok=True)
    text = (configured or "").strip()
    if not text:
        return fallback, ""
    try:
        path = Path(text).expanduser()
    except (OSError, ValueError):
        return fallback, f"目录配置无效，已改用 {fallback}。"
    if is_foreign_user_path(path):
        return fallback, f"配置里的目录是另一台电脑的路径：{path}。已改用 {fallback}。"
    try:
        if path.exists() and path.is_dir():
            return path, ""
    except OSError:
        pass
    try:
        path.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            return path, ""
    except OSError as exc:
        return fallback, f"无法使用目录 {path}（{exc}）。已改用 {fallback}。"
    return fallback, f"无法使用目录 {path}。已改用 {fallback}。"


def sanitize_portable_paths(config: AppConfig) -> AppConfig:
    payload = config.model_dump()
    changed = False
    for key in ("source_dir", "output_dir"):
        raw = str((payload.get("paths") or {}).get(key) or "").strip()
        if raw and is_foreign_user_path(raw):
            payload.setdefault("paths", {})[key] = ""
            changed = True
    if not changed:
        return config
    return AppConfig.model_validate(payload)


def load_config() -> AppConfig:
    path = config_path()
    try:
        if not path.exists():
            config = apply_builtin_defaults(AppConfig())
            _try_save(config)
            return config
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        loaded = AppConfig.model_validate(payload)
        config = apply_builtin_defaults(loaded)
        config = sanitize_portable_paths(config)
        raw_prompt = ""
        if isinstance(payload, dict):
            raw_prompt = str((payload.get("api") or {}).get("remix_prompt") or "")
        if config.model_dump() != loaded.model_dump() or effective_remix_prompt(raw_prompt) != raw_prompt:
            _try_save(config)
        return config
    except (OSError, json.JSONDecodeError, UnicodeError, ValidationError, ValueError):
        try:
            if path.exists():
                path.replace(path.with_name("config.bad.json"))
        except OSError:
            pass
        config = apply_builtin_defaults(AppConfig())
        _try_save(config)
        return config


def save_config(config: AppConfig) -> None:
    path = config_path()
    path.write_text(config.model_dump_json(indent=2), encoding="utf-8")


def output_dir(config: AppConfig) -> Path:
    path, _note = resolve_work_dir(config.paths.output_dir, data_dir() / "output")
    return path


def source_dir(config: AppConfig) -> Path:
    path, _note = resolve_work_dir(config.paths.source_dir, data_dir() / "source")
    return path


def source_dir_status(config: AppConfig) -> tuple[Path, str]:
    return resolve_work_dir(config.paths.source_dir, data_dir() / "source")


def output_dir_status(config: AppConfig) -> tuple[Path, str]:
    return resolve_work_dir(config.paths.output_dir, data_dir() / "output")
