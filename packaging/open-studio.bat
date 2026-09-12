@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "APP=%~dp0"
if exist "%~dp0WallpaperStudio.exe" goto :found
if exist "%~dp0WallpaperStudio\WallpaperStudio.exe" (
  set "APP=%~dp0WallpaperStudio"
  goto :found
)

echo 找不到 WallpaperStudio.exe。
echo.
echo 请把整个 client-Windows 压缩包解压到一个新文件夹，再双击「1-打开壁纸工坊.bat」。
echo 不要进 Lib 或 Include，那些只是运行库，不是程序。
echo WallpaperStudio.exe 按名称会排在一堆 .dll 后面，请往下滚。
pause
exit /b 1

:found
cd /d "%APP%"
set "APP=%CD%"
set "PATH=%APP%;%PATH%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -LiteralPath '%APP%' -File -ErrorAction SilentlyContinue | Unblock-File" >nul 2>&1

if exist "%APP%\_internal\python312.dll" if not exist "%APP%\python312.dll" (
  echo 这是旧的 PyInstaller 包装，会弹出 Failed to load Python DLL。
  echo 请删掉整个 WallpaperStudio 文件夹，再解压最新的 client-Windows。
  pause
  exit /b 1
)

if not exist "%APP%\python312.dll" (
  echo 缺少 python312.dll。请删掉整个文件夹后重新解压 GitHub 的 client-Windows。
  pause
  exit /b 1
)

if not exist "%APP%\pythonw.exe" (
  echo 缺少 pythonw.exe。请删掉整个文件夹后重新解压最新包。
  pause
  exit /b 1
)

start "" "%APP%\WallpaperStudio.exe"
