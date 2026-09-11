@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
set "PATH=%~dp0;%PATH%"

if not exist "%~dp0WallpaperStudio.exe" (
  echo 当前目录没有 WallpaperStudio.exe。
  echo 请先解压整个 WallpaperStudio 文件夹，再双击本文件。
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -LiteralPath '%~dp0' -File -ErrorAction SilentlyContinue | Unblock-File" >nul 2>&1

if exist "%~dp0_internal\python312.dll" if not exist "%~dp0python312.dll" (
  echo 这是旧的 PyInstaller 包装，会弹出 Failed to load Python DLL。
  echo 请删掉整个 WallpaperStudio 文件夹，再解压最新的 client-Windows。
  pause
  exit /b 1
)

if not exist "%~dp0python312.dll" (
  echo 缺少 python312.dll。请删掉整个文件夹后重新解压 GitHub 的 client-Windows。
  pause
  exit /b 1
)

if not exist "%~dp0pythonw.exe" (
  echo 缺少 pythonw.exe。请删掉整个文件夹后重新解压最新包。
  pause
  exit /b 1
)

start "" "%~dp0WallpaperStudio.exe"
