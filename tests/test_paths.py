from wallpaper_studio.paths import app_root, web_dir


def test_web_assets_exist():
    folder = web_dir()
    assert (folder / "index.html").exists()
    assert (folder / "studio.css").exists()
    assert (folder / "studio.js").exists()


def test_app_root_is_repo():
    root = app_root()
    assert (root / "run.py").exists()
    assert (root / "start.bat").exists()
    assert (root / "打开壁纸工坊.bat").exists()
