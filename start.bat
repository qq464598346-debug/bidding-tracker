@echo off
chcp 65001 >nul 2>&1
title 运营商招投标智能监控系统 v4.0
echo.
echo ═══════════════════════════════════════════
echo   运营商招投标智能监控系统 v4.0
echo   数据源: 乙方宝 + 百度寻标宝
echo ═══════════════════════════════════════════
echo.

cd /d "%~dp0spider"

:: 检查Python
where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.9+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查依赖
python -c "import flask, httpx, bs4" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖...
    pip install -r requirements.txt -q
)

:: 启动服务
echo [启动] 正在启动爬虫+API服务...
echo [地址] http://localhost:8765
echo [提示] 按 Ctrl+C 停止服务
echo.
python main.py

pause
