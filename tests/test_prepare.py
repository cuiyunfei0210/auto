import pytest

from wallpaper_studio.models import Account, ApiSettings, AppConfig, PathSettings
from wallpaper_studio.prepare import prepare_images
from wallpaper_studio.relay import ApiError
from wallpaper_studio.storage import save_config, source_dir
from tests.helpers import make_png


def test_prepare_translates_image_generation_error(studio_home, monkeypatch):
    config = AppConfig(
        mode="remix_then_upload",
        api=ApiSettings(api_key="sk-test"),
        paths=PathSettings(source_dir=str(studio_home / "source"), output_dir=str(studio_home / "output")),
        accounts=[Account(username="demo1", password="123123", upload_count=1, interval_seconds=0)],
    )
    save_config(config)
    make_png(source_dir(config) / "night.png")

    monkeypatch.setattr(
        "wallpaper_studio.prepare.RelayClient.generate_title",
        lambda self, stem: "静谧星河夜语",
    )

    def boom(self, source, dest_dir, title):
        raise ApiError("Tool choice 'image_generation' not found in 'tools' parameter.")

    monkeypatch.setattr("wallpaper_studio.prepare.RelayClient.remix_image", boom)

    with pytest.raises(ApiError, match="跳过二创"):
        prepare_images(config)


def test_prepare_skips_title_api_for_image_models(studio_home, monkeypatch):
    config = AppConfig(
        mode="upload_only",
        api=ApiSettings(api_key="sk-test", filename_model="gpt-image-2"),
        paths=PathSettings(source_dir=str(studio_home / "source"), output_dir=str(studio_home / "output")),
        accounts=[Account(username="demo1", password="123123", upload_count=1, interval_seconds=0)],
    )
    save_config(config)
    make_png(source_dir(config) / "night.png")
    logs: list[str] = []

    def boom(self, stem):
        raise AssertionError("title API should not be called for gpt-image-2")

    monkeypatch.setattr("wallpaper_studio.prepare.RelayClient.generate_title", boom)
    prepared = prepare_images(config, logs.append)
    assert prepared[0].name.startswith("night")
    assert any("不能写标题" in line for line in logs)


def test_prepare_reads_nested_source_image(studio_home):
    config = AppConfig(
        mode="upload_only",
        paths=PathSettings(source_dir=str(studio_home / "source"), output_dir=str(studio_home / "output")),
        accounts=[Account(username="demo1", password="123123", upload_count=1, interval_seconds=0)],
    )
    save_config(config)
    make_png(studio_home / "source" / "batch1" / "night.png")
    prepared = prepare_images(config)
    assert len(prepared) == 1
    assert prepared[0].exists()


def test_prepare_decrements_remix_remaining(studio_home, monkeypatch):
    config = AppConfig(
        mode="remix_then_upload",
        api=ApiSettings(api_key="sk-test"),
        paths=PathSettings(source_dir=str(studio_home / "source"), output_dir=str(studio_home / "output")),
        accounts=[Account(username="demo1", password="123123", upload_count=2, interval_seconds=0)],
    )
    save_config(config)
    make_png(studio_home / "source" / "one.png")
    make_png(studio_home / "source" / "two.png", (10, 20, 30))
    ticks: list[tuple[int, int]] = []

    def fake_remix(self, source, dest_dir, title):
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / f"{title}.png"
        path.write_bytes(source.read_bytes())
        return path

    monkeypatch.setattr("wallpaper_studio.prepare.RelayClient.remix_image", fake_remix)
    logs: list[str] = []
    prepared = prepare_images(config, logs.append, progress=lambda left, total: ticks.append((left, total)))
    assert len(prepared) == 2
    assert ticks[0] == (2, 2)
    assert ticks[1] == (1, 2)
    assert ticks[2] == (0, 2)
    assert any("不会强制黄昏" in line for line in logs)
