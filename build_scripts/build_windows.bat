@echo off
echo ========================================
echo Building PowerMonitor for Windows...
echo ========================================
echo.

REM Check if in virtual environment
if not defined VIRTUAL_ENV (
    echo WARNING: Not in a virtual environment
    echo It's recommended to use a virtual environment
    echo.
    set /p CONTINUE="Continue anyway? (y/n): "
    if /i not "%CONTINUE%"=="y" exit /b 1
)

echo Installing dependencies...
pip install -r requirements.txt
pip install -r requirements-dev.txt
echo.

echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo.

echo Running PyInstaller...
pyinstaller PowerMonitor.spec
echo.

if exist "dist\PowerMonitor" (
    echo ========================================
    echo Build successful!
    echo Executable location: dist\PowerMonitor\PowerMonitor.exe
    echo ========================================
    echo.
    echo You can now run: dist\PowerMonitor\PowerMonitor.exe
    echo.
    explorer dist\PowerMonitor
) else (
    echo ========================================
    echo Build FAILED!
    echo Check the output above for errors
    echo ========================================
    exit /b 1
)

pause
