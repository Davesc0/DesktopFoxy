@echo off
setlocal
cd /d "%~dp0"
set "PY=venv\Scripts\python.exe"

if not exist "%PY%" (
    echo Creating virtual environment...
    python -m venv venv || goto :fail
)

echo Installing dependencies...
"%PY%" -m pip install -q --disable-pip-version-check -r requirements-build.txt || goto :fail

echo Building...
"%PY%" -m PyInstaller DesktopFoxy.spec --clean --noconfirm --log-level WARN || goto :fail

echo.
echo Done: dist\DesktopFoxy.exe
exit /b 0

:fail
echo.
echo BUILD FAILED - see the errors above.
pause
exit /b 1
