@echo off
echo ====================================
echo DesktopFoxy EXE Builder
echo ====================================
echo.

REM Check if venv exists
if not exist "venv\" (
    echo [1/4] Creating virtual environment...
    python -m venv venv
    echo.
) else (
    echo [1/4] Virtual environment already exists
    echo.
)

REM Activate venv
echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Install dependencies
echo [3/4] Installing dependencies...
pip install -q PyQt6 Pillow pystray pyinstaller
echo Dependencies installed!
echo.

REM Build EXE
echo [4/4] Building EXE with PyInstaller...
pyinstaller DesktopFoxy_FIXED.spec --clean
echo.

if exist "dist\DesktopFoxy.exe" (
    echo ====================================
    echo BUILD SUCCESSFUL!
    echo ====================================
    echo.
    echo Your EXE is ready: dist\DesktopFoxy.exe
    echo.
    echo Press any key to run the EXE...
    pause > nul
    start dist\DesktopFoxy.exe
) else (
    echo ====================================
    echo BUILD FAILED!
    echo ====================================
    echo Please check the error messages above
    pause
)
