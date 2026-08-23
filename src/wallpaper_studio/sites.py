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


def category_label(value: str) -> str:
    """Map a CQwall id, English name, or Chinese name to the Chinese label."""
    mapped = map_category(value)
    for cid, name in CQWALL_CATEGORY_LABELS:
        if mapped == cid:
            return name
    return (value or "").strip()


_CATEGORY_HINTS = (
    ("军事", ("soldier", "military", "weapon", "tactical", "helicopter", "rifle", "士兵", "军事", "战机")),
    ("动漫", ("anime", "动漫")),
    ("汽车", ("car", "cars", "vehicle", "汽车")),
    ("动物", ("animal", "animals", "dog", "cat", "动物")),
    ("游戏", ("game", "games", "游戏")),
    ("美女", ("girl", "美女")),
    ("都市", ("urban", "city street", "都市")),
    ("宇宙", ("space", "galaxy", "universe", "宇宙")),
    ("风景", ("landscape", "scenery", "mountain", "lake", "风景")),
)


def infer_category_label(text: str) -> str:
    import re

    raw = text or ""
    lowered = raw.lower()
    for label, needles in _CATEGORY_HINTS:
        for needle in needles:
            if needle.isascii():
                if re.search(rf"\b{re.escape(needle.lower())}\b", lowered):
                    return label
            elif needle in raw:
                return label
    return ""


def parse_category_reply(text: str) -> tuple[str, str]:
    """Parse vision output into (CQwall category label, subject description)."""
    category = ""
    subject = ""
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        key, _, rest = stripped.partition(":")
        label = key.strip().lower()
        value = rest.strip().strip(" \"'`")
        if label in {"category", "分类"} and value:
            category = category_label(value) or infer_category_label(value)
        elif label in {"subject", "主体"} and value:
            subject = value
    if not category:
        category = infer_category_label(text)
    if not subject:
        subject = (text or "").strip()
    return category, subject


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
