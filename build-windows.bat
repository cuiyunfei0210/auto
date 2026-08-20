@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title 打包壁纸工坊
echo Building WallpaperStudio.exe for Windows...

if not exist ".venv\Scripts\python.exe" (
  echo Run start.bat once first so the virtualenv exists.
  pause
  exit /b 1
)

.venv\Scripts\python.exe -m pip install -U pyinstaller
if errorlevel 1 goto :fail

.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --name WallpaperStudio ^
  --add-data "src/wallpaper_studio/web;wallpaper_studio/web" ^
  --hidden-import uvicorn.logging ^
  --hidden-import uvicorn.lifespan.on ^
  --hidden-import uvicorn.protocols.http.auto ^
  --hidden-import uvicorn.protocols.websockets.auto ^
  --hidden-import wallpaper_studio.web ^
  run.py
if errorlevel 1 goto :fail

echo.
echo Done: dist\WallpaperStudio\WallpaperStudio.exe
echo Copy that folder to any Windows PC. Double-click the exe.
echo Playwright Chromium must still be installed: playwright install chromium
pause
goto :eof

:fail
echo Build failed.
pause
exit /b 1
