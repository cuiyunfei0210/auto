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
    assert "PLAYWRIGHT_BROWSERS_PATH" in workflow
    assert "playwright install chromium" in workflow
    spec = (root / "wallpaper_studio.spec").read_text(encoding="utf-8")
    assert ".local-browsers" in spec
    assert 'sys.platform != "darwin"' in spec
    assert "console=False" in spec
    workflow = (root / ".github" / "workflows" / "build-client.yml").read_text(encoding="utf-8")
    assert "if: runner.os != 'macOS'" in workflow
    text = (root / "build-windows.bat").read_text(encoding="utf-8", errors="replace")
    assert "WallpaperStudio.exe" in text
    assert "PLAYWRIGHT_BROWSERS_PATH" in text
    ui = (root / "src" / "wallpaper_studio" / "web" / "studio.js").read_text(encoding="utf-8")
    assert "function renderLogs" in ui
    assert "function notify(" in ui
    assert "localStartProblems" in ui
    assert "refreshCounts" in ui
    assert "parseJson" in ui
    assert "任务已开始" in ui
    assert "remix_progress" in ui
    assert "/api/shutdown" in ui
    assert "btn-quit" in ui
    html = (root / "src" / "wallpaper_studio" / "web" / "index.html").read_text(encoding="utf-8")
    assert "待二创" in html
    assert "退出程序" in html
    assert "??" not in ui
    assert "replaceAll" not in ui
    assert "studio.js" in html
    assert "charset=" in html
    launcher = (root / "src" / "wallpaper_studio" / "__main__.py").read_text(encoding="utf-8")
    assert "access_log=False" in launcher
    assert "btn-quit" in html


def test_studio_js_has_valid_syntax():
    import shutil
    import subprocess

    root = Path(__file__).resolve().parents[1]
    js = root / "src" / "wallpaper_studio" / "web" / "studio.js"
    text = js.read_text(encoding="utf-8")
    for line in text.splitlines():
        if "??" in line and "||" in line:
            raise AssertionError(f"do not mix ?? and || on one line: {line.strip()}")
    node = shutil.which("node")
    if node:
        subprocess.run([node, "--check", str(js)], check=True)
