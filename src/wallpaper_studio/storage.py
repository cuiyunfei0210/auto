from __future__ import annotations

import json
import os
from pathlib import Path

from wallpaper_studio.models import AppConfig, apply_builtin_defaults
from wallpaper_studio.paths import app_root

DEFAULT_PORT = 8765
CONFIG_FILENAME = "config.json"


def data_dir() -> Path:
    raw = os.environ.get("WALLPAPER_STUDIO_HOME")
    if raw:
        path = Path(raw).expanduser()
    else:
        path = app_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return data_dir() / CONFIG_FILENAME


def load_config() -> AppConfig:
    path = config_path()
    if not path.exists():
        config = apply_builtin_defaults(AppConfig())
        save_config(config)
        return config
    payload = json.loads(path.read_text(encoding="utf-8"))
    loaded = AppConfig.model_validate(payload)
    config = apply_builtin_defaults(loaded)
    if config.model_dump() != loaded.model_dump():
        save_config(config)
    return config


def save_config(config: AppConfig) -> None:
    path = config_path()
    path.write_text(config.model_dump_json(indent=2), encoding="utf-8")


def output_dir(config: AppConfig) -> Path:
    configured = config.paths.output_dir.strip()
    path = Path(configured).expanduser() if configured else data_dir() / "output"
    path.mkdir(parents=True, exist_ok=True)
    return path


def source_dir(config: AppConfig) -> Path:
    configured = config.paths.source_dir.strip()
    path = Path(configured).expanduser() if configured else data_dir() / "source"
    path.mkdir(parents=True, exist_ok=True)
    return path
