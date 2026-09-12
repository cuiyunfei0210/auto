from wallpaper_studio.paths import app_root, archive_temp_warning, is_archive_temp_path, web_dir
from pathlib import Path


def test_web_assets_exist():
    folder = web_dir()
    assert (folder / "index.html").exists()
    assert (folder / "studio.css").exists()
    assert (folder / "studio.js").exists()


def test_packaged_env_marks_frozen(monkeypatch):
    from wallpaper_studio.paths import is_frozen

    monkeypatch.setattr("wallpaper_studio.paths.sys.frozen", False, raising=False)
    monkeypatch.setenv("WALLPAPER_STUDIO_PACKAGED", "1")
    assert is_frozen() is True


def test_app_root_is_repo(monkeypatch):
    monkeypatch.delenv("WALLPAPER_STUDIO_PACKAGED", raising=False)
    monkeypatch.delenv("WALLPAPER_STUDIO_ROOT", raising=False)
    monkeypatch.setattr("wallpaper_studio.paths.sys.frozen", False, raising=False)
    root = app_root()
    assert (root / "run.py").exists()
    assert (root / "start.bat").exists()
    assert (root / "打开壁纸工坊.bat").exists()


def test_detects_winrar_temp_path():
    rar = Path(r"C:\Users\Administrator\AppData\Local\Temp\Rar$EXa4584.40542.rartemp\WallpaperStudio")
    assert is_archive_temp_path(rar)
    assert is_archive_temp_path(Path(r"C:\Users\foo\AppData\Local\Temp\7zO1234\WallpaperStudio"))
    assert not is_archive_temp_path(Path(r"D:\WallpaperStudio"))


def test_archive_warning_only_when_frozen_from_temp(monkeypatch):
    rar = Path(r"C:\Users\Administrator\AppData\Local\Temp\Rar$EXa4584.40542.rartemp\WallpaperStudio")
    monkeypatch.setattr("wallpaper_studio.paths.is_frozen", lambda: False)
    assert archive_temp_warning(rar) is None
    monkeypatch.setattr("wallpaper_studio.paths.is_frozen", lambda: True)
    warning = archive_temp_warning(rar)
    assert warning is not None
    assert "解压" in warning
