@echo off
chcp 65001 >nul
echo ============================================
echo   运营商招投标信息跟踪平台 - 一键部署到 GitHub
echo ============================================
echo.

:: 检查git是否安装
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Git，请先安装 Git: https://git-scm.com/downloads
    pause
    exit /b 1
)

cd /d "%~dp0"

echo [1/5] 检查 Git 状态...
if not exist ".git" (
    echo [初始化] 创建 Git 仓库...
    git init
)

echo.
echo [2/5] 配置文件已准备就绪...
echo   - index.html (主应用, 含60+条数据)
echo   - .github/workflows/deploy.yml (自动部署)
echo   - README.md (项目文档)
echo.

echo [3/5] 请输入你的 GitHub 信息（用于创建远程仓库）:
set /p GITHUB_USER="GitHub 用户名: "
if "%GITHUB_USER%"=="" (
    echo [取消] 未输入用户名
    pause
    exit /b 1
)
set /p REPO_NAME="仓库名称 (默认: bidding-tracker): "
if "%REPO_NAME%"=="" set REPO_NAME=bidding-tracker

echo.
echo [4/5] 准备部署文件...

:: 添加所有文件
git add index.html README.md .github .gitignore

if %errorlevel% neq 0 (
    echo [警告] 没有需要提交的更改
) else (
    git commit -m "🚀 部署: 运营商招投标信息跟踪平台 v3.0"
    
    :: 设置远程仓库
    git remote remove origin >nul 2>nul
    git remote add origin https://github.com/%GITHUB_USER%/%REPO_NAME%.git
    
    echo.
    echo [5/5] 推送到 GitHub...
    echo.
    
    git push -u origin main 2>nul || git push -u origin master 2>nul
    
    if %errorlevel% equ 0 (
        echo.
        echo ============================================
        echo   ✅ 部署成功！
        echo ============================================
        echo.
        echo   📡 你的网站地址:
        echo   https://%GITHUB_USER%.github.io/%REPO_NAME%/
        echo.
        echo   ⏱️ GitHub Pages 可能在1-2分钟后生效
        echo   如需启用 Pages: 进入仓库 → Settings → Pages → Source 选 main 分支
        echo.
    ) else (
        echo.
        echo ============================================
        echo   ❌ 推送失败
        echo ============================================
        echo.
        echo   可能的原因:
        echo   1. 仓库 "%REPO_NAME%" 尚不存在于 GitHub
        echo      请先在 GitHub 上创建该仓库
        echo      https://github.com/new?repo_name=%REPO_NAME%
        echo.
        echo   2. 认证问题 — 请确保配置了 SSH Key 或使用 HTTPS 认证
        echo.
        echo   手动操作步骤:
        echo   1. 在 GitHub 创建新仓库: %REPO_NAME%
        echo   2. 运行以下命令推送:
        echo      git remote set-url origin https://github.com/%GITHUB_USER%/%REPO_NAME%.git
        echo      git push -u origin main
        echo.
    )
)

pause
