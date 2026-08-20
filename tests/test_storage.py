from pathlib import Path
import json

from wallpaper_studio.models import DEFAULT_REMIX_PROMPT, AppConfig, PathSettings
from wallpaper_studio.storage import (
    is_foreign_user_path,
    load_config,
    resolve_work_dir,
    sanitize_portable_paths,
)


def test_foreign_windows_path_detected(monkeypatch):
    monkeypatch.setenv("USERNAME", "Bob")
    monkeypatch.setenv("USER", "Bob")
    assert is_foreign_user_path(r"C:\Users\Administrator\Desktop\WallpaperStudio\data\source")
    assert not is_foreign_user_path(r"C:\Users\Bob\Desktop\WallpaperStudio\data\source")
    assert not is_foreign_user_path(r"D:\WallpaperStudio\data\source")


def test_resolve_work_dir_ignores_other_pc_user_path(tmp_path, monkeypatch):
    monkeypatch.setenv("USERNAME", "Bob")
    monkeypatch.setenv("USER", "Bob")
    fallback = tmp_path / "source"
    fallback.mkdir()
    resolved, note = resolve_work_dir(
        r"C:\Users\Administrator\Desktop\WallpaperStudio\data\source",
        fallback,
    )
    assert resolved == fallback
    assert "另一台电脑" in note


def test_sanitize_portable_paths_clears_foreign_dirs(monkeypatch):
    monkeypatch.setenv("USERNAME", "Bob")
    monkeypatch.setenv("USER", "Bob")
    config = AppConfig(
        paths=PathSettings(
            source_dir=r"C:\Users\Administrator\Desktop\WallpaperStudio\data\source",
            output_dir=r"C:\Users\Administrator\Desktop\WallpaperStudio\data\output",
        )
    )
    cleaned = sanitize_portable_paths(config)
    assert cleaned.paths.source_dir == ""
    assert cleaned.paths.output_dir == ""


def test_load_config_recovers_from_corrupt_json(studio_home):
    bad = studio_home / "config.json"
    bad.write_text("{not json", encoding="utf-8")
    config = load_config()
    assert config.accounts
    assert (studio_home / "config.bad.json").exists()
    assert (studio_home / "config.json").exists()


def test_load_config_fills_blank_remix_prompt(studio_home):
    path = studio_home / "config.json"
    path.write_text(
        json.dumps(
            {
                "api": {"remix_prompt": ""},
                "accounts": [{"username": "demo@cqwall.com", "password": "123123"}],
            }
        ),
        encoding="utf-8",
    )
    config = load_config()
    assert config.api.remix_prompt == DEFAULT_REMIX_PROMPT
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["api"]["remix_prompt"] == DEFAULT_REMIX_PROMPT
