from pathlib import Path

import pytest

from wallpaper_studio.jobs import run_job
from wallpaper_studio.models import Account, AppConfig, NetworkSettings, PathSettings, SiteProfile, apply_builtin_defaults
from wallpaper_studio.storage import save_config, source_dir
from tests.helpers import make_png


class RecordingUploader:
    def __init__(self) -> None:
        self.events: list[tuple] = []

    async def start_account(self, account, proxy=None) -> None:
        self.events.append(("start", account.username, proxy))

    async def upload_image(self, image: Path, title: str, category: str) -> None:
        current = ""
        for event in reversed(self.events):
            if event[0] == "start":
                current = event[1]
                break
        self.events.append(("upload", current, image.name, title, category))

    async def close(self) -> None:
        self.events.append(("close",))


async def test_job_uploads_one_account_then_switches(studio_home):
    config = AppConfig(
        mode="upload_only",
        paths=PathSettings(source_dir=str(studio_home / "source"), output_dir=str(studio_home / "output")),
        site=SiteProfile(category_value="风景"),
        accounts=[
            Account(username="demo1", password="123123", upload_count=2, interval_seconds=0.01),
            Account(username="demo2", password="123123", upload_count=2, interval_seconds=0.01),
        ],
    )
    save_config(config)
    folder = source_dir(config)
    for index in range(3):
        make_png(folder / f"pic{index}.png", (10 * index, 80, 120))

    waits: list[float] = []
    uploader = RecordingUploader()

    async def fake_sleep(seconds: float) -> None:
        waits.append(seconds)

    result = await run_job(config, sleep=fake_sleep, uploader=uploader)
    assert result["uploaded"] == 3
    assert result["accounts_used"] == 2
    kinds = [event[0] for event in uploader.events]
    assert kinds == [
        "start",
        "upload",
        "upload",
        "close",
        "start",
        "upload",
        "close",
        "close",
    ]
    assert uploader.events[0][1] == "demo1"
    assert uploader.events[4][1] == "demo2"
    assert uploader.events[1][1] == "demo1"
    assert uploader.events[5][1] == "demo2"
    assert waits == [0.01]


async def test_job_gives_each_account_its_own_proxy(studio_home):
    config = AppConfig(
        mode="upload_only",
        paths=PathSettings(source_dir=str(studio_home / "source"), output_dir=str(studio_home / "output")),
        site=SiteProfile(),
        accounts=[
            Account(username="demo1", password="123123", upload_count=1, interval_seconds=0),
            Account(username="demo2", password="123123", upload_count=1, interval_seconds=0),
        ],
        network=NetworkSettings(
            proxy_enabled=True,
            unique_ip_per_account=True,
            proxies=["http://10.0.0.1:8080", "http://10.0.0.2:8080"],
        ),
    )
    save_config(config)
    make_png(source_dir(config) / "a.png")
    make_png(source_dir(config) / "b.png", (10, 20, 30))
    uploader = RecordingUploader()
    await run_job(config, uploader=uploader)
    starts = [event for event in uploader.events if event[0] == "start"]
    assert starts[0] == ("start", "demo1", "http://10.0.0.1:8080")
    assert starts[1] == ("start", "demo2", "http://10.0.0.2:8080")


async def test_job_requires_accounts_before_prepare(studio_home):
    config = AppConfig(mode="remix_then_upload", accounts=[])
    save_config(config)
    with pytest.raises(ValueError, match="还没有添加账号"):
        await run_job(config)


def test_apply_defaults_adds_cqwall_and_switches_old_relay():
    config = AppConfig.model_validate(
        {
            "api": {"base_url": "https://api.newxxt.top", "api_key": "sk-old"},
            "accounts": [{"username": "1252597792@qq.com", "password": "123123"}],
        }
    )
    updated = apply_builtin_defaults(config)
    assert updated.api.base_url == "https://xmapi.site"
    assert updated.api.api_key.startswith("sk-")
    assert updated.accounts[0].username == "ari-ihcot@linshi-mail.com"
    assert all(item.username != "1252597792@qq.com" for item in updated.accounts)


def test_apply_defaults_switches_xbhuiz_to_xmapi():
    config = AppConfig.model_validate({"api": {"base_url": "https://xbhuiz.com", "api_key": ""}})
    updated = apply_builtin_defaults(config)
    assert updated.api.base_url == "https://xmapi.site"
    assert updated.api.api_key.startswith("sk-")
