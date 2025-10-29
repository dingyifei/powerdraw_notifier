#!/bin/bash
set -e

echo "========================================"
echo "Building PowerMonitor for macOS..."
echo "========================================"
echo

# Check if in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "WARNING: Not in a virtual environment"
    echo "It's recommended to use a virtual environment"
    read -p "Continue anyway? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
        exit 1
    fi
fi

echo "Installing dependencies..."
pip install -r requirements.txt
pip install -r requirements-dev.txt
echo

echo "Cleaning previous builds..."
rm -rf build dist
echo

echo "Running PyInstaller..."
pyinstaller PowerMonitor.spec
echo

if [ -d "dist/PowerMonitor" ]; then
    echo "========================================"
    echo "Build successful!"
    echo "Application location: dist/PowerMonitor/"
    echo "========================================"
    echo
    echo "You can now run: dist/PowerMonitor/PowerMonitor"
    echo
    open dist/PowerMonitor
else
    echo "========================================"
    echo "Build FAILED!"
    echo "Check the output above for errors"
    echo "========================================"
    exit 1
fi
