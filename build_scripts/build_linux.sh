#!/bin/bash
set -e

echo "========================================"
echo "Building PowerMonitor for Linux..."
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
    echo "Executable location: dist/PowerMonitor/PowerMonitor"
    echo "========================================"
    echo
    echo "To run the application:"
    echo "  cd dist/PowerMonitor"
    echo "  ./PowerMonitor"
    echo
    # Make executable
    chmod +x dist/PowerMonitor/PowerMonitor
    echo "Executable permissions set"
else
    echo "========================================"
    echo "Build FAILED!"
    echo "Check the output above for errors"
    echo "========================================"
    exit 1
fi
