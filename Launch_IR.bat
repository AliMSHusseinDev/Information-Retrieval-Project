@echo off
setlocal
cd /d "%~dp0"
if exist "dist\IR_Search_Engine\IR_Search_Engine.exe" (
    "dist\IR_Search_Engine\IR_Search_Engine.exe"
    exit /b
)
if not exist ".venv\Scripts\python.exe" (
    py -3.12 -m venv .venv
    if errorlevel 1 goto failed
    ".venv\Scripts\python.exe" -m pip install -r requirements-gui.txt
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" launcher.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo Launch failed. See the message above and README.md for setup instructions.
pause
exit /b 1
