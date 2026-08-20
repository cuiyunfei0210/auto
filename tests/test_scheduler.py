from pathlib import Path

import pytest

from wallpaper_studio.files import empty_source_message, list_images, sanitize_filename, unique_path
from wallpaper_studio.models import Account, NetworkSettings
from wallpaper_studio.scheduler import (
    ProxyAssignmentError,
    plan_account_batches,
    proxy_for_account_index,
)


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


def test_list_images_finds_nested_and_jfif(tmp_path: Path):
    (tmp_path / "album").mkdir()
    (tmp_path / "album" / "shot.jfif").write_bytes(b"x")
    (tmp_path / "notes.txt").write_bytes(b"x")
    names = [path.name for path in list_images(tmp_path)]
    assert names == ["shot.jfif"]


def test_empty_source_message_lists_other_files(tmp_path: Path):
    (tmp_path / "readme.txt").write_text("x", encoding="utf-8")
    text = empty_source_message(tmp_path)
    assert "没有图片" in text
    assert "readme.txt" in text


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
        unique_ip_per_account=False,
        rotate_every_accounts=5,
        proxies=["http://p1", "http://p2"],
    )
    assert proxy_for_account_index(0, network) == "http://p1"
    assert proxy_for_account_index(4, network) == "http://p1"
    assert proxy_for_account_index(5, network) == "http://p2"
    assert proxy_for_account_index(10, network) == "http://p1"
    disabled = NetworkSettings(proxy_enabled=False, proxies=["http://p1"])
    assert proxy_for_account_index(0, disabled) is None


def test_unique_ip_assigns_one_proxy_per_account():
    network = NetworkSettings(
        proxy_enabled=True,
        unique_ip_per_account=True,
        proxies=["http://p1", "http://p2", "http://p3"],
    )
    accounts = [
        Account(username="a", password="p", upload_count=1),
        Account(username="b", password="p", upload_count=1),
        Account(username="c", password="p", upload_count=1, proxy="socks5://own:1"),
    ]
    batches = plan_account_batches([Path("1.png"), Path("2.png"), Path("3.png")], accounts, network)
    assert [batch.proxy for batch in batches] == ["http://p1", "http://p2", "socks5://own:1"]


def test_unique_ip_rejects_shared_or_missing_proxy():
    network = NetworkSettings(
        proxy_enabled=True,
        unique_ip_per_account=True,
        proxies=["http://only-one"],
    )
    accounts = [
        Account(username="a", password="p", upload_count=1),
        Account(username="b", password="p", upload_count=1),
    ]
    with pytest.raises(ProxyAssignmentError, match="没有独立出口"):
        plan_account_batches([Path("1.png"), Path("2.png")], accounts, network)

    same = NetworkSettings(proxy_enabled=True, unique_ip_per_account=True, proxies=[])
    twins = [
        Account(username="a", password="p", upload_count=1, proxy="http://same"),
        Account(username="b", password="p", upload_count=1, proxy="http://same"),
    ]
    with pytest.raises(ProxyAssignmentError, match="共用了同一出口"):
        plan_account_batches([Path("1.png"), Path("2.png")], twins, same)
