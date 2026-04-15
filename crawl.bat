@echo off
chcp 65001 >nul 2>&1
title 运营商招投标数据采集 v4.0
echo.
echo ═══════════════════════════════════════════
echo   运营商招投标数据采集工具 v4.0
echo   数据源: 乙方宝 + 百度寻标宝
echo ═══════════════════════════════════════════
echo.

cd /d "%~dp0spider"

where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python
    pause
    exit /b 1
)

python -c "import flask, httpx, bs4" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖...
    pip install -r requirements.txt -q
)

echo [开始] 正在从乙方宝+寻标宝抓取最新招标数据...
echo.
python main.py --crawl

echo.
echo [完成] 数据采集结束！
echo [查看] 请启动API服务后访问 http://localhost:8765 查看数据
pause
