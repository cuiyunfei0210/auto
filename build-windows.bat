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

echo [1/2] 使用官方嵌入式 Python 打包（不再用 PyInstaller 的 _internal）...
"%PYEXE%" "%~dp0packaging\build_windows_embed.py"
if errorlevel 1 goto :fail

echo [2/2] 完成

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
