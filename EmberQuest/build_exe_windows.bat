@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run start_windows.bat first, then close the game and run this file again.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install pyinstaller
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onedir --windowed --name EmberQuest --add-data "assets;assets" main.py
if errorlevel 1 goto failed
echo Done. Copy the ENTIRE dist\EmberQuest folder to another Windows computer.
pause
exit /b 0
:failed
echo Build failed. Read the error message above.
pause
exit /b 1
