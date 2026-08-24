import pytest

from wallpaper_studio.files import list_images
from wallpaper_studio.models import Account, ApiSettings, AppConfig, PathSettings
from wallpaper_studio.prepare import prepare_images
from wallpaper_studio.relay import ApiError
from wallpaper_studio.storage import output_dir, save_config, source_dir
from tests.helpers import make_png


def test_prepare_translates_image_generation_error(studio_home, monkeypatch):
    config = AppConfig(
        mode="remix_then_upload",
        api=ApiSettings(api_key="sk-test", filename_prompt=""),
        paths=PathSettings(source_dir=str(studio_home / "source"), output_dir=str(studio_home / "output")),
        accounts=[Account(username="demo1", password="123123", upload_count=1, interval_seconds=0)],
    )
    save_config(config)
    make_png(source_dir(config) / "night.png")

    monkeypatch.setattr(
        "wallpaper_studio.prepare.RelayClient.generate_title",
        lambda self, stem, image=None: "静谧星河夜语",
    )

    def boom(self, source, dest_dir, title):
        raise ApiError("Tool choice 'image_generation' not found in 'tools' parameter.")

    monkeypatch.setattr("wallpaper_studio.prepare.RelayClient.remix_image", boom)

    logs: list[str] = []
    with pytest.raises(ApiError, match="全部二创都失败了"):
        prepare_images(config, logs.append)
    assert any("跳过 night.png" in line for line in logs)
    assert any("继续下一张" in line for line in logs)


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

    def boom(self, stem, image=None):
        raise AssertionError("title API should not be called for gpt-image-2")

    monkeypatch.setattr("wallpaper_studio.prepare.RelayClient.generate_title", boom)
    prepared = prepare_images(config, logs.append)
    assert prepared[0].path.name.startswith("night")
    assert prepared[0].title == "night"
    assert any("根据图片写标题" in line for line in logs)


def test_prepare_reads_nested_source_image(studio_home):
    config = AppConfig(
        mode="upload_only",
        api=ApiSettings(filename_prompt=""),
        paths=PathSettings(source_dir=str(studio_home / "source"), output_dir=str(studio_home / "output")),
        accounts=[Account(username="demo1", password="123123", upload_count=1, interval_seconds=0)],
    )
    save_config(config)
    make_png(studio_home / "source" / "batch1" / "night.png")
    prepared = prepare_images(config)
    assert len(prepared) == 1
    assert prepared[0].path.exists()
    assert prepared[0].path.parent == studio_home / "source" / "batch1"


def test_prepare_decrements_remix_remaining(studio_home, monkeypatch):
    config = AppConfig(
        mode="remix_then_upload",
        api=ApiSettings(api_key="sk-test", filename_prompt=""),
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


def test_prepare_skips_failed_remix_and_continues(studio_home, monkeypatch):
    config = AppConfig(
        mode="remix_then_upload",
        api=ApiSettings(api_key="sk-test", filename_prompt=""),
        paths=PathSettings(source_dir=str(studio_home / "source"), output_dir=str(studio_home / "output")),
        accounts=[Account(username="demo1", password="123123", upload_count=2, interval_seconds=0)],
    )
    save_config(config)
    make_png(studio_home / "source" / "bad.png")
    make_png(studio_home / "source" / "good.png", (10, 20, 30))

    def fake_remix(self, source, dest_dir, title):
        if source.name == "bad.png":
            raise ApiError("生成的图片可能违反了关于与第三方内容相似性的防护限制。")
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / f"{title}.png"
        path.write_bytes(source.read_bytes())
        return path

    monkeypatch.setattr("wallpaper_studio.prepare.RelayClient.remix_image", fake_remix)
    logs: list[str] = []
    prepared = prepare_images(config, logs.append)
    assert len(prepared) == 1
    assert prepared[0].path.name.startswith("good")
    assert any("跳过 bad.png" in line for line in logs)
    assert any("中转站拦截" in line for line in logs)
    assert any("成功 1 张，跳过 1 张" in line for line in logs)


def test_upload_only_keeps_source_images_and_does_not_copy(studio_home):
    config = AppConfig(
        mode="upload_only",
        api=ApiSettings(filename_prompt=""),
        paths=PathSettings(source_dir=str(studio_home / "source"), output_dir=str(studio_home / "output")),
        accounts=[Account(username="demo1", password="123123", upload_count=1, interval_seconds=0)],
    )
    save_config(config)
    source = make_png(source_dir(config) / "keep.png")
    dest = output_dir(config)
    dest.mkdir(parents=True, exist_ok=True)
    prepared = prepare_images(config)
    assert len(prepared) == 1
    assert prepared[0].path == source
    assert prepared[0].title == "keep"
    assert list_images(dest) == []


def test_remix_clears_leftover_output_so_count_matches_source(studio_home, monkeypatch):
    config = AppConfig(
        mode="remix_then_upload",
        api=ApiSettings(api_key="sk-test", filename_prompt=""),
        paths=PathSettings(source_dir=str(studio_home / "source"), output_dir=str(studio_home / "output")),
        accounts=[Account(username="demo1", password="123123", upload_count=2, interval_seconds=0)],
    )
    save_config(config)
    make_png(source_dir(config) / "one.png")
    dest = output_dir(config)
    dest.mkdir(parents=True, exist_ok=True)
    leftover = dest / "one-2.png"
    leftover.write_bytes(b"old")
    (dest / "stale.png").write_bytes(b"old")

    def fake_remix(self, source, dest_dir, title):
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / f"{title}.png"
        path.write_bytes(source.read_bytes())
        return path

    monkeypatch.setattr("wallpaper_studio.prepare.RelayClient.remix_image", fake_remix)
    logs: list[str] = []
    prepared = prepare_images(config, logs.append)
    assert len(prepared) == 1
    assert not leftover.exists()
    assert not (dest / "stale.png").exists()
    assert prepared[0].path.name == "one.png"
    assert any("上次留下" in line for line in logs)


def test_prepare_skips_duplicate_nested_source(studio_home, monkeypatch):
    config = AppConfig(
        mode="remix_then_upload",
        api=ApiSettings(api_key="sk-test", filename_prompt=""),
        paths=PathSettings(source_dir=str(studio_home / "source"), output_dir=str(studio_home / "output")),
        accounts=[Account(username="demo1", password="123123", upload_count=3, interval_seconds=0)],
    )
    save_config(config)
    original = make_png(studio_home / "source" / "ce8257.jpg")
    nested = studio_home / "source" / "backup"
    nested.mkdir()
    (nested / "ce8257.jpg").write_bytes(original.read_bytes())
    seen: list[str] = []

    def fake_remix(self, source, dest_dir, title):
        seen.append(source.name)
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / f"{title}.png"
        path.write_bytes(source.read_bytes())
        return path

    monkeypatch.setattr("wallpaper_studio.prepare.RelayClient.remix_image", fake_remix)
    prepared = prepare_images(config)
    assert seen == ["ce8257.jpg"]
    assert len(prepared) == 1


def test_prepare_sends_image_to_title_model(studio_home, monkeypatch):
    config = AppConfig(
        mode="upload_only",
        api=ApiSettings(api_key="sk-test", filename_model="gpt-4o-mini"),
        paths=PathSettings(source_dir=str(studio_home / "source"), output_dir=str(studio_home / "output")),
        accounts=[Account(username="demo1", password="123123", upload_count=1, interval_seconds=0)],
    )
    save_config(config)
    source = make_png(source_dir(config) / "night.png")
    seen: dict = {}

    def fake_title(self, stem, image=None):
        seen["stem"] = stem
        seen["image"] = image
        return "红旗街景黄昏"

    monkeypatch.setattr("wallpaper_studio.prepare.RelayClient.generate_title", fake_title)
    prepared = prepare_images(config)
    assert seen["stem"] == "night"
    assert seen["image"] == source
    assert prepared[0].title == "红旗街景黄昏"
    assert prepared[0].path == source


def test_prepare_stops_before_the_next_image(studio_home, monkeypatch):
    from wallpaper_studio.control import JobStopped

    config = AppConfig(
        mode="remix_then_upload",
        api=ApiSettings(api_key="sk-test", filename_prompt=""),
        paths=PathSettings(source_dir=str(studio_home / "source"), output_dir=str(studio_home / "output")),
        accounts=[Account(username="demo1", password="123123", upload_count=3, interval_seconds=0)],
    )
    save_config(config)
    make_png(studio_home / "source" / "one.png")
    make_png(studio_home / "source" / "two.png", (10, 20, 30))
    seen: list[str] = []

    def fake_remix(self, source, dest_dir, title):
        seen.append(source.name)
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / f"{title}.png"
        path.write_bytes(source.read_bytes())
        return path

    monkeypatch.setattr("wallpaper_studio.prepare.RelayClient.remix_image", fake_remix)
    logs: list[str] = []

    def stop_after_first() -> bool:
        return len(seen) >= 1

    with pytest.raises(JobStopped, match="已手动停止"):
        prepare_images(config, logs.append, stop_check=stop_after_first)
    assert seen == ["one.png"] or len(seen) == 1
    assert any("已停止" in line for line in logs)
