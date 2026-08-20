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
