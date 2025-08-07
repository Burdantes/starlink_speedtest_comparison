@echo off
REM Starlink Speedtest Comparison - Installation Script for Windows
REM This script installs all dependencies and sets up the environment

echo 🚀 Starlink Speedtest Comparison - Installation Script
echo ==================================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher and try again
    pause
    exit /b 1
)

echo ✅ Python detected

REM Check if pip is installed
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: pip is not installed
    echo Please install pip and try again
    pause
    exit /b 1
)

echo ✅ pip detected

REM Upgrade pip
echo 📦 Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo 📦 Installing Python dependencies...
python -m pip install -r requirements.txt

REM Install package in development mode
echo 🔧 Installing package in development mode...
python -m pip install -e .

REM Create necessary directories
echo 📁 Creating necessary directories...
if not exist "data" mkdir data
if not exist "data\processed" mkdir data\processed
if not exist "output" mkdir output
if not exist "output\visualizations" mkdir output\visualizations
if not exist "logs" mkdir logs

echo ✅ Directories created

REM Check Google Cloud SDK
gcloud --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Google Cloud SDK not found
    echo    To use BigQuery features, install Google Cloud SDK:
    echo    https://cloud.google.com/sdk/docs/install
) else (
    echo ✅ Google Cloud SDK is installed
    
    REM Check authentication
    gcloud auth application-default print-access-token >nul 2>&1
    if errorlevel 1 (
        echo ⚠️  Google Cloud authentication not configured
        echo    Run: gcloud auth application-default login
    ) else (
        echo ✅ Google Cloud authentication is configured
    )
)

echo.
echo 🎉 Installation completed successfully!
echo.
echo 📋 Next steps:
echo 1. Set up Google Cloud authentication (if using BigQuery features):
echo    gcloud auth application-default login
echo 2. Configure your Google Cloud project ID in the collector files
echo 3. Run data collection:
echo    python generating_data.py
echo 4. Generate visualizations:
echo    python visualizations\generate_visualizations.py
echo 5. Start the web application:
echo    cd web ^&^& python app.py
echo.
echo 📚 For more information, see the README.md file
pause
