@echo off
REM 打包 NovelSplitter 为单文件 exe（需先 uv venv ^&^& uv pip install -r requirements.txt）
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\pyinstaller.exe (
    echo [错误] 未找到 .venv，请先创建虚拟环境并安装依赖：
    echo   uv venv .venv
    echo   uv pip install --python .venv\Scripts\python.exe -r requirements.txt
    exit /b 1
)
.venv\Scripts\pyinstaller.exe --noconfirm --onefile --windowed --name NovelSplitter main.py
if errorlevel 1 exit /b 1
echo.
echo 打包完成：dist\NovelSplitter.exe
