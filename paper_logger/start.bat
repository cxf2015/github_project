@echo off
chcp 65001 >nul
echo ========================================
echo   Paper Logger - 论文阅读记录系统
echo ========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.7+
    pause
    exit /b 1
)

echo [信息] 正在检查依赖...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo [信息] 正在安装依赖...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
) else (
    echo [信息] 依赖已安装
)

echo.
echo [信息] 正在启动服务器...
echo [信息] 请在浏览器中访问：http://localhost:5000
echo [提示] 按 Ctrl+C 可停止服务器
echo.
echo ========================================
echo.

python app.py

pause
