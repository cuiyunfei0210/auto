@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
set "PATH=%~dp0;%~dp0_internal;%PATH%"

if not exist "%~dp0WallpaperStudio.exe" (
  echo 当前目录没有 WallpaperStudio.exe。
  echo 请先解压整个 WallpaperStudio 文件夹，再双击本文件。
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -LiteralPath '%~dp0' -File -ErrorAction SilentlyContinue | Unblock-File; if (Test-Path -LiteralPath '%~dp0_internal') { Get-ChildItem -LiteralPath '%~dp0_internal' -File -ErrorAction SilentlyContinue | Unblock-File }" >nul 2>&1

if not exist "%~dp0_internal\python312.dll" (
  if exist "%~dp0python312.dll" copy /Y "%~dp0python312.dll" "%~dp0_internal\python312.dll" >nul
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

for %%A in ("%~dp0_internal\python312.dll") do set "PYDLL_SIZE=%%~zA"
if "%PYDLL_SIZE%"=="" set "PYDLL_SIZE=0"
if %PYDLL_SIZE% LSS 1000000 (
  echo python312.dll 文件太小（%PYDLL_SIZE% 字节），多半是解压不完整或被杀毒软件清空。
  echo 请从 GitHub Actions 重新下载 client-Windows，并检查 360/Windows Defender 隔离区。
  pause
  exit /b 1
)

if not exist "%~dp0_internal\vcruntime140.dll" if exist "%~dp0vcruntime140.dll" copy /Y "%~dp0vcruntime140.dll" "%~dp0_internal\vcruntime140.dll" >nul
if not exist "%~dp0_internal\vcruntime140_1.dll" if exist "%~dp0vcruntime140_1.dll" copy /Y "%~dp0vcruntime140_1.dll" "%~dp0_internal\vcruntime140_1.dll" >nul
if not exist "%~dp0_internal\vcruntime140.dll" (
  echo 缺少运行库：vcruntime140.dll
  echo 请安装 Microsoft Visual C++ 2015-2022 x64：
  echo https://aka.ms/vs/17/release/vc_redist.x64.exe
  start "" "https://aka.ms/vs/17/release/vc_redist.x64.exe"
  pause
  exit /b 1
)

if not exist "%~dp0_internal\_socket.pyd" (
  echo 缺少运行文件：_internal\_socket.pyd
  echo.
  echo 这是旧包或不完整解压。请删掉整个 WallpaperStudio 文件夹，
  echo 再重新下载 GitHub Actions 里最新一次 Build client app 的 client-Windows。
  echo.
  pause
  exit /b 1
)

start "" "%~dp0WallpaperStudio.exe"
