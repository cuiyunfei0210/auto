from pathlib import Path

from wallpaper_studio.files import list_images, sanitize_filename, unique_path
from wallpaper_studio.models import Account, NetworkSettings
from wallpaper_studio.scheduler import plan_account_batches, proxy_for_account_index


def test_sanitize_filename_strips_illegal_chars():
    assert sanitize_filename('  晨雾/森林:"1"  ') == "晨雾森林1"
    assert sanitize_filename("shot.jpg") == "shot"
    assert sanitize_filename("   ") == "wallpaper"


def test_list_images_sorted(tmp_path: Path):
    (tmp_path / "b.PNG").write_bytes(b"x")
    (tmp_path / "a.jpg").write_bytes(b"x")
    (tmp_path / "notes.txt").write_bytes(b"x")
    names = [path.name for path in list_images(tmp_path)]
    assert names == ["a.jpg", "b.PNG"]


def test_unique_path_increments(tmp_path: Path):
    first = unique_path(tmp_path, "sky", ".png")
    first.write_text("1")
    second = unique_path(tmp_path, "sky", ".png")
    assert second.name == "sky-2.png"


def test_plan_finishes_one_account_before_next(tmp_path: Path):
    images = [tmp_path / f"{index}.png" for index in range(5)]
    accounts = [
        Account(username="a", password="p", upload_count=2, interval_seconds=1),
        Account(username="b", password="p", upload_count=2, interval_seconds=1),
        Account(username="c", password="p", upload_count=9, interval_seconds=1),
    ]
    batches = plan_account_batches(images, accounts)
    assert [batch.account.username for batch in batches] == ["a", "b", "c"]
    assert [path.name for path in batches[0].images] == ["0.png", "1.png"]
    assert [path.name for path in batches[1].images] == ["2.png", "3.png"]
    assert [path.name for path in batches[2].images] == ["4.png"]


def test_proxy_rotates_every_five_accounts():
    network = NetworkSettings(
        proxy_enabled=True,
        rotate_every_accounts=5,
        proxies=["http://p1", "http://p2"],
    )
    assert proxy_for_account_index(0, network) == "http://p1"
    assert proxy_for_account_index(4, network) == "http://p1"
    assert proxy_for_account_index(5, network) == "http://p2"
    assert proxy_for_account_index(10, network) == "http://p1"
    disabled = NetworkSettings(proxy_enabled=False, proxies=["http://p1"])
    assert proxy_for_account_index(0, disabled) is None
