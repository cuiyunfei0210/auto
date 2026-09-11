@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title 打包成 exe

echo.
echo   正在把壁纸工坊打包成 Windows 桌面程序
echo   完成后会出现：dist\WallpaperStudio\WallpaperStudio.exe
echo.

set "VENV=%~dp0.venv"
set "PYEXE=%VENV%\Scripts\python.exe"

if not exist "%PYEXE%" (
  call :find_python
  if errorlevel 1 goto :fail
  echo 正在创建运行环境...
  %PYTHON% -m venv "%VENV%"
  if errorlevel 1 goto :fail
)

"%PYEXE%" -c "import fastapi,uvicorn,playwright,httpx,PIL,pydantic,webview" 2>nul
if errorlevel 1 (
  echo 正在安装程序组件...
  "%PYEXE%" -m pip install -U pip
  "%PYEXE%" -m pip install -e "%~dp0"
  if errorlevel 1 goto :fail
)

echo [1/4] 安装打包工具 PyInstaller...
"%PYEXE%" -m pip install -U pyinstaller
if errorlevel 1 goto :fail

echo [2/4] 把 Chromium 装进 Playwright 目录，便于打进 exe...
set "PLAYWRIGHT_BROWSERS_PATH=0"
"%PYEXE%" -m playwright install chromium
if errorlevel 1 goto :fail

echo [3/4] 开始打包，可能要几分钟，窗口不要关...
"%PYEXE%" -m PyInstaller --noconfirm --clean wallpaper_studio.spec
if errorlevel 1 goto :fail

echo [4/4] 写入使用说明、VC 运行库和启动检查...
"%PYEXE%" "%~dp0packaging\windows_runtime.py" "%~dp0dist\WallpaperStudio"
if errorlevel 1 goto :fail
copy /Y "%~dp0packaging\exe-readme.txt" "%~dp0dist\WallpaperStudio\使用说明.txt" >nul
copy /Y "%~dp0packaging\open-studio.bat" "%~dp0dist\WallpaperStudio\打开壁纸工坊.bat" >nul

echo.
echo ========================================
echo  打包完成
echo  打开这个文件夹：
echo  %~dp0dist\WallpaperStudio
echo  双击其中的 WallpaperStudio.exe
echo ========================================
echo.
explorer "%~dp0dist\WallpaperStudio"
echo 按任意键关闭本窗口（不影响已经生成的 exe）
pause
goto :eof

:find_python
where py >nul 2>&1
if not errorlevel 1 (
  set "PYTHON=py -3"
  py -3 -c "import sys; raise SystemExit(0 if sys.version_info>=(3,11) else 1)" 2>nul
  if not errorlevel 1 exit /b 0
)
where python >nul 2>&1
if not errorlevel 1 (
  set "PYTHON=python"
  python -c "import sys; raise SystemExit(0 if sys.version_info>=(3,11) else 1)" 2>nul
  if not errorlevel 1 exit /b 0
)
echo 没有找到 Python 3.11 或更高版本。
echo 请先安装：https://www.python.org/downloads/windows/
echo 安装时勾选 Add python.exe to PATH。
exit /b 1

:fail
echo.
echo 打包失败。请确认已安装 Python，并把上面的报错发出来。
pause
exit /b 1
