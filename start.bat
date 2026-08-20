@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title 壁纸工坊
echo.
echo   壁纸工坊
echo   Windows 上请双击本文件打开。第一次会自动安装依赖，请勿关闭窗口。
echo.

set "VENV=%~dp0.venv"
set "PYEXE=%VENV%\Scripts\python.exe"

if not exist "%PYEXE%" (
  call :find_python
  if errorlevel 1 goto :fail
  echo [1/3] 正在创建运行环境...
  %PYTHON% -m venv "%VENV%"
  if errorlevel 1 goto :fail
)

"%PYEXE%" -c "import fastapi,uvicorn,playwright,httpx,PIL,pydantic" 2>nul
if errorlevel 1 (
  echo [2/3] 正在安装程序组件...
  "%PYEXE%" -m pip install -U pip
  if exist "%~dp0pyproject.toml" (
    "%PYEXE%" -m pip install -e "%~dp0"
  ) else (
    "%PYEXE%" -m pip install -r "%~dp0requirements.txt"
  )
  if errorlevel 1 goto :fail
)

if not exist "%VENV%\.chromium-ok" (
  echo [3/3] 正在安装 Chromium（上传网页需要）...
  "%PYEXE%" -m playwright install chromium
  if errorlevel 1 goto :fail
  echo ok>"%VENV%\.chromium-ok"
)

echo.
echo 正在启动，浏览器会自动打开 http://127.0.0.1:8765
echo 用完前请不要关闭这个黑窗口。
echo.
"%PYEXE%" "%~dp0run.py"
if errorlevel 1 goto :fail
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
echo 启动失败，请把上面的英文/中文报错发出来。
pause
exit /b 1
