@echo off
setlocal
cd /d "%~dp0"
echo Ember Quest - starting...
if exist ".venv\Scripts\python.exe" goto run
py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    py -3.12 -m venv .venv
    goto checkvenv
)
py -3 --version >nul 2>&1
if not errorlevel 1 (
    py -3 -m venv .venv
    goto checkvenv
)
python --version >nul 2>&1
if errorlevel 1 (
    echo Python was not found. Install Python 3.12 from python.org.
    pause
    exit /b 1
)
python -m venv .venv
:checkvenv
if not exist ".venv\Scripts\python.exe" (
    echo Could not create the virtual environment. See the error above.
    pause
    exit /b 1
)
:run
".venv\Scripts\python.exe" -c "import pygame; assert pygame.version.ver == '2.6.1'" >nul 2>&1
if errorlevel 1 (
    echo Installing Pygame. Internet is required for the first launch.
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Install failed. Use Python 3.12 and check your internet connection.
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 pause
endlocal
