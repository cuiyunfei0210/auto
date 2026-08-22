from __future__ import annotations

from wallpaper_studio.models import SiteProfile

CQWALL_CATEGORIES = {
    "animals": "1",
    "动物": "1",
    "military fan": "2",
    "military": "2",
    "军事": "2",
    "军事迷": "2",
    "cars": "3",
    "汽车": "3",
    "movie": "4",
    "电影": "4",
    "era": "5",
    "时代": "5",
    "celebrity": "6",
    "明星": "6",
    "universe": "7",
    "宇宙": "7",
    "girl": "8",
    "美女": "8",
    "scenery": "9",
    "风景": "9",
    "anime": "10",
    "动漫": "10",
    "games": "17",
    "游戏": "17",
    "urban": "18",
    "都市": "18",
}

# Live CQwall nav order: Games, Anime, Scenery, Girl, Universe, Celebrity,
# Era, Movie, Cars, Military fan, Animals, Urban.
CQWALL_CATEGORY_LABELS = (
    ("1", "动物"),
    ("2", "军事"),
    ("3", "汽车"),
    ("4", "电影"),
    ("5", "时代"),
    ("6", "明星"),
    ("7", "宇宙"),
    ("8", "美女"),
    ("9", "风景"),
    ("10", "动漫"),
    ("17", "游戏"),
    ("18", "都市"),
)


def cqwall_category_hint() -> str:
    return " / ".join(f"{cid} {name}" for cid, name in CQWALL_CATEGORY_LABELS)


def map_category(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if text.isdigit():
        return text
    mapped = CQWALL_CATEGORIES.get(text.lower()) or CQWALL_CATEGORIES.get(text)
    return mapped or text


def category_choices(value: str) -> list[str]:
    """Value/id/English/Chinese aliases to try against a CQwall/Layui select."""
    raw = (value or "").strip()
    mapped = map_category(raw)
    names: list[str] = []
    for item in (raw, mapped):
        if item and item not in names:
            names.append(item)
    for name, cid in CQWALL_CATEGORIES.items():
        if cid == mapped or name == raw or name == raw.lower():
            if name not in names:
                names.append(name)
            if cid not in names:
                names.append(cid)
    return names


def demo_site(base: str = "http://127.0.0.1:8765") -> SiteProfile:
    return SiteProfile(
        login_url=f"{base}/demo/login",
        upload_url=f"{base}/demo/upload",
        username_selector="#username",
        password_selector="#password",
        login_button_selector="button[type=submit]",
        file_input_selector="input[type=file]",
        title_selector="#title",
        category_selector="#category",
        category_value="风景",
        submit_selector="#submit-upload",
        success_text="上传成功",
        headless=True,
    )


def cqwall_site() -> SiteProfile:
    return SiteProfile(
        login_url="https://www.cqwall.com/",
        upload_url="https://www.cqwall.com/index/index/center.html",
        open_login_selector='.header .login a[lay-on="page-login"]',
        username_selector='#layer-user input[name="email"]',
        password_selector='#layer-user input[name="password"]',
        login_button_selector='#layer-user button[lay-filter="login"]',
        login_success_text="Login successful",
        logged_in_selector=".logged_in",
        open_upload_selector='a[lay-on="page-upload"]',
        file_input_selector="#ID-upload-demo-drag input[type=file]",
        file_uploaded_text="Uploaded",
        title_selector='#layer-upload input[name="title"]',
        category_selector='#layer-upload select[name="category"]',
        category_value="9",
        agree_selector='#layer-upload input[name="remember"]',
        submit_selector='#layer-upload button[lay-filter="wallpaper"]',
        success_text="",
        min_width=0,
        min_height=0,
        headless=True,
    )


SITE_PRESETS = {
    "cqwall": cqwall_site(),
    "demo": demo_site(),
}
