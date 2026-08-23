from pathlib import Path

from wallpaper_studio.files import filter_by_min_size
from wallpaper_studio.models import SiteProfile
from wallpaper_studio.sites import cqwall_category_hint, cqwall_site, map_category, parse_category_reply
from tests.helpers import make_png


def test_parse_category_reply_keeps_military_and_subject():
    category, subject = parse_category_reply(
        "CATEGORY: 军事\nSUBJECT: a soldier in tactical gear holding a rifle"
    )
    assert category == "军事"
    assert "soldier" in subject


def test_parse_category_reply_infers_military_from_prose():
    category, subject = parse_category_reply("modern soldier in tactical gear with a rifle")
    assert category == "军事"
    assert "soldier" in subject


def test_map_category_accepts_chinese_and_ids():
    assert map_category("风景") == "9"
    assert map_category("Scenery") == "9"
    assert map_category("9") == "9"
    assert map_category("动漫") == "10"
    assert map_category("军事") == "2"
    assert map_category("都市") == "18"
    assert map_category("美女") == "8"


def test_cqwall_category_hint_lists_all_live_ids():
    hint = cqwall_category_hint()
    assert hint == (
        "1 动物 / 2 军事 / 3 汽车 / 4 电影 / 5 时代 / 6 明星 / "
        "7 宇宙 / 8 美女 / 9 风景 / 10 动漫 / 17 游戏 / 18 都市"
    )
    html = (Path(__file__).resolve().parents[1] / "src/wallpaper_studio/web/index.html").read_text(
        encoding="utf-8"
    )
    assert hint in html


def test_category_choices_include_id_and_names():
    from wallpaper_studio.sites import category_choices

    names = category_choices("9")
    assert "9" in names
    assert "风景" in names
    assert "scenery" in names


def test_cqwall_preset_points_at_live_site():
    site = cqwall_site()
    assert site.login_url == "https://www.cqwall.com/"
    assert site.upload_url.endswith("/index/index/center.html")
    assert site.open_login_selector == '.header .login a[lay-on="page-login"]'
    assert site.file_input_selector == "#ID-upload-demo-drag input[type=file]"
    assert site.file_uploaded_text == "Uploaded"
    assert site.min_width == 0
    assert site.min_height == 0


def test_site_profile_ignores_saved_size_limits():
    site = SiteProfile(min_width=1920, min_height=1080)
    assert site.min_width == 0
    assert site.min_height == 0


def test_filter_skips_small_images(tmp_path: Path):
    small = make_png(tmp_path / "small.png")
    kept, skipped = filter_by_min_size([small], 1920, 1080)
    assert kept == []
    assert skipped and "small.png" in skipped[0]
