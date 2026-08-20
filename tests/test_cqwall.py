from pathlib import Path

from wallpaper_studio.files import filter_by_min_size
from wallpaper_studio.models import SiteProfile
from wallpaper_studio.sites import cqwall_site, map_category
from tests.helpers import make_png


def test_map_category_accepts_chinese_and_ids():
    assert map_category("风景") == "9"
    assert map_category("Scenery") == "9"
    assert map_category("9") == "9"
    assert map_category("动漫") == "10"


def test_cqwall_preset_points_at_live_site():
    site = cqwall_site()
    assert site.login_url == "https://www.cqwall.com/"
    assert site.upload_url.endswith("/index/index/center.html")
    assert site.open_login_selector == '.header .login a[lay-on="page-login"]'
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
