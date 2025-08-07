#!/bin/bash

# Starlink Speedtest Comparison - Installation Script
# This script installs all dependencies and sets up the environment

set -e  # Exit on any error

echo "🚀 Starlink Speedtest Comparison - Installation Script"
echo "=================================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "Please install Python 3.8 or higher and try again"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Error: Python 3.8 or higher is required"
    echo "Current version: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION detected"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ Error: pip3 is not installed"
    echo "Please install pip3 and try again"
    exit 1
fi

echo "✅ pip3 detected"

# Upgrade pip
echo "📦 Upgrading pip..."
python3 -m pip install --upgrade pip

# Install requirements
echo "📦 Installing Python dependencies..."
python3 -m pip install -r requirements.txt

# Install package in development mode
echo "🔧 Installing package in development mode..."
python3 -m pip install -e .

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p data/processed output/visualizations logs

echo "✅ Directories created"

# Check Google Cloud SDK
if command -v gcloud &> /dev/null; then
    echo "✅ Google Cloud SDK is installed"
    
    # Check authentication
    if gcloud auth application-default print-access-token &> /dev/null; then
        echo "✅ Google Cloud authentication is configured"
    else
        echo "⚠️  Google Cloud authentication not configured"
        echo "   Run: gcloud auth application-default login"
    fi
else
    echo "⚠️  Google Cloud SDK not found"
    echo "   To use BigQuery features, install Google Cloud SDK:"
    echo "   https://cloud.google.com/sdk/docs/install"
fi

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Set up Google Cloud authentication (if using BigQuery features):"
echo "   gcloud auth application-default login"
echo "2. Configure your Google Cloud project ID in the collector files"
echo "3. Run data collection:"
echo "   python3 generating_data.py"
echo "4. Generate visualizations:"
echo "   python3 visualizations/generate_visualizations.py"
echo "5. Start the web application:"
echo "   cd web && python3 app.py"
echo ""
echo "📚 For more information, see the README.md file"
