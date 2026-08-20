from pathlib import Path


def test_windows_packaging_files_exist():
    root = Path(__file__).resolve().parents[1]
    assert (root / "build-windows.bat").exists()
    assert (root / "start.bat").exists()
    assert (root / "packaging" / "exe-readme.txt").exists()
    assert (root / "wallpaper_studio.spec").exists()
    workflow = (root / ".github" / "workflows" / "build-client.yml").read_text(encoding="utf-8")
    assert "name: Build client app" in workflow
    assert "windows-latest" in workflow
    text = (root / "build-windows.bat").read_text(encoding="utf-8", errors="replace")
    assert "WallpaperStudio.exe" in text
    assert "wallpaper_studio.spec" in text
