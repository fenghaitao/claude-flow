@echo off
echo 🌊 Claude-Flow Python Installation
echo ========================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.8+ first.
    pause
    exit /b 1
)

echo ✅ Python detected
echo.

REM Install dependencies
echo 📦 Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

REM Install package
echo 🔧 Installing package...
python -m pip install -e .
if errorlevel 1 (
    echo ❌ Failed to install package
    pause
    exit /b 1
)

REM Test installation
echo 🧪 Testing installation...
python test_imports.py
if errorlevel 1 (
    echo ❌ Installation test failed
    pause
    exit /b 1
)

echo.
echo 🎉 Installation completed successfully!
echo.
echo Next steps:
echo 1. Set your CLAUDE_API_KEY environment variable
echo 2. Run: python -m claude_flow.cli.main init
echo 3. Run: python -m claude_flow.cli.main --help
echo.
echo For more information, see README.md
echo.
pause
