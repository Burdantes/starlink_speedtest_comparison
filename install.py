#!/usr/bin/env python3
"""
Installation script for Starlink Speedtest Comparison Project

This script will:
1. Check Python version
2. Install required dependencies
3. Set up Google Cloud authentication (if needed)
4. Create necessary directories
"""

import subprocess
import sys
import os
import platform
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")

def install_requirements():
    """Install requirements from requirements.txt."""
    print("\n📦 Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        sys.exit(1)

def install_package():
    """Install the package in development mode."""
    print("\n🔧 Installing package in development mode...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."])
        print("✅ Package installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing package: {e}")
        sys.exit(1)

def create_directories():
    """Create necessary directories if they don't exist."""
    print("\n📁 Creating necessary directories...")
    directories = [
        "data",
        "data/processed",
        "output",
        "output/visualizations",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def check_google_cloud_setup():
    """Check if Google Cloud is set up."""
    print("\n☁️  Checking Google Cloud setup...")
    
    # Check if Google Cloud SDK is installed
    try:
        subprocess.run(["gcloud", "--version"], capture_output=True, check=True)
        print("✅ Google Cloud SDK is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  Google Cloud SDK not found")
        print("   To use BigQuery features, install Google Cloud SDK:")
        print("   https://cloud.google.com/sdk/docs/install")
    
    # Check if application default credentials are set
    try:
        result = subprocess.run(["gcloud", "auth", "application-default", "print-access-token"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Google Cloud authentication is configured")
        else:
            print("⚠️  Google Cloud authentication not configured")
            print("   Run: gcloud auth application-default login")
    except FileNotFoundError:
        print("⚠️  Google Cloud SDK not available for authentication check")

def print_next_steps():
    """Print next steps for the user."""
    print("\n🎉 Installation completed successfully!")
    print("\n📋 Next steps:")
    print("1. Set up Google Cloud authentication (if using BigQuery features):")
    print("   gcloud auth application-default login")
    print("2. Configure your Google Cloud project ID in the collector files")
    print("3. Run data collection:")
    print("   python generating_data.py")
    print("4. Generate visualizations:")
    print("   python visualizations/generate_visualizations.py")
    print("5. Start the web application:")
    print("   cd web && python app.py")
    print("\n📚 For more information, see the README.md file")

def main():
    """Main installation function."""
    print("🚀 Starlink Speedtest Comparison - Installation Script")
    print("=" * 60)
    
    # Check Python version
    check_python_version()
    
    # Install requirements
    install_requirements()
    
    # Install package
    install_package()
    
    # Create directories
    create_directories()
    
    # Check Google Cloud setup
    check_google_cloud_setup()
    
    # Print next steps
    print_next_steps()

if __name__ == "__main__":
    main()
