@echo off

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo   Python 3 is required. Install it from https://python.org
    echo.
    pause
    exit /b 1
)

echo.
echo   Starting Octobot...
echo.

python -c "import anthropic, flask, httpx, rich" >nul 2>nul
if %errorlevel% neq 0 (
    echo   Installing dependencies...
    if exist requirements.txt (
        pip install -r requirements.txt --quiet
    ) else (
        pip install . --quiet
    )
    python -m playwright install chromium 2>nul
)

python main.py
