from pathlib import Path


def test_windows_packaging_files_exist():
    root = Path(__file__).resolve().parents[1]
    assert (root / "build-windows.bat").exists()
    assert (root / "start.bat").exists()
    assert (root / "packaging" / "exe-readme.txt").exists()
    assert (root / "packaging" / "open-studio.bat").exists()
    assert (root / "packaging" / "windows_runtime.py").exists()
    assert (root / "wallpaper_studio.spec").exists()
    workflow = (root / ".github" / "workflows" / "build-client.yml").read_text(encoding="utf-8")
    assert "name: Build client app" in workflow
    assert "windows-latest" in workflow
    assert "PLAYWRIGHT_BROWSERS_PATH" in workflow
    assert "playwright install chromium" in workflow
    assert "python312.dll" in workflow
    assert "_socket.pyd" in workflow
    assert "vcruntime140_1.dll" in workflow
    assert "pw-browsers" in workflow
    assert "include-hidden-files: true" in workflow
    assert "windows_runtime.py" in workflow
    assert "Smoke-test Windows exe" in workflow
    assert "open-studio.bat" in workflow
    spec = (root / "wallpaper_studio.spec").read_text(encoding="utf-8")
    assert ".local-browsers" in spec
    assert 'sys.platform != "darwin"' in spec
    assert "console=False" in spec
    assert "_windows_runtime" in spec
    assert "vcruntime140.dll" in spec or "windows_runtime" in spec
    assert "python312.dll" in spec or "windows_runtime" in spec
    assert "pw-browsers" in spec
    assert "_socket.pyd" in spec or "STDLIB_PYD_NAMES" in (root / "packaging" / "windows_runtime.py").read_text(encoding="utf-8")
    assert '"_socket"' in spec
    assert "multiprocessing.freeze_support" in (root / "run.py").read_text(encoding="utf-8")
    assert "webview" in spec
    assert "wallpaper_studio.desktop" in spec
    project = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "pywebview" in project
    workflow = (root / ".github" / "workflows" / "build-client.yml").read_text(encoding="utf-8")
    assert "if: runner.os != 'macOS'" in workflow
    text = (root / "build-windows.bat").read_text(encoding="utf-8", errors="replace")
    assert "WallpaperStudio.exe" in text
    assert "PLAYWRIGHT_BROWSERS_PATH" in text
    assert "windows_runtime.py" in text
    assert "打开壁纸工坊.bat" in text
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
    assert "FIXED_API_BASE" in ui
    assert "filename_api_key" in ui
    assert "relay_preset" not in ui
    html = (root / "src" / "wallpaper_studio" / "web" / "index.html").read_text(encoding="utf-8")
    assert "待二创" in html
    assert "退出程序" in html
    assert "relay_preset" not in html
    assert "api.newxxt.top" in html
    assert "1920x1080" in html
    assert "??" not in ui
    assert "replaceAll" not in ui
    assert "studio.js" in html
    assert "charset=" in html
    assert "btn-quit" in html
    launcher = (root / "src" / "wallpaper_studio" / "__main__.py").read_text(encoding="utf-8")
    assert "access_log=False" in launcher
    readme = (root / "packaging" / "exe-readme.txt").read_text(encoding="utf-8")
    assert "python312.dll" in readme
    launcher_bat = (root / "packaging" / "open-studio.bat").read_text(encoding="utf-8")
    assert "_socket.pyd" in launcher_bat
    assert "vcruntime140.dll" in launcher_bat
    assert "Unblock-File" in launcher_bat
    runtime = (root / "packaging" / "windows_runtime.py").read_text(encoding="utf-8")
    assert "vcruntime140_1.dll" in runtime
    assert "ucrtbase.dll" in runtime
    assert "api-ms-win-crt-" in runtime
    assert "vc_redist.x64.exe" in readme
    assert "程序窗口" in readme
    assert "WebView2" in readme
    assert "系统浏览器" in readme


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
