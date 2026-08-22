@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

if not exist "%~dp0WallpaperStudio.exe" (
  echo 当前目录没有 WallpaperStudio.exe。
  echo 请先解压整个 WallpaperStudio 文件夹，再双击本文件。
  pause
  exit /b 1
)

if not exist "%~dp0_internal\python312.dll" (
  echo 缺少运行文件：_internal\python312.dll
  echo.
  echo 这通常是因为没有解压完整：
  echo 1. 不要只拷一个 exe 到桌面
  echo 2. 不要在压缩包 / WinRAR 窗口里直接打开
  echo 3. 覆盖旧版时，先删掉整个 WallpaperStudio 文件夹，再解压新的
  echo 4. 微信/QQ 传的 zip 可能损坏，请改用浏览器下载 GitHub 的 client-Windows
  echo.
  pause
  exit /b 1
)

start "" "%~dp0WallpaperStudio.exe"
