@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m venv .venv-build
if errorlevel 1 goto failed
".venv-build\Scripts\python.exe" -m pip install -r requirements.txt PyInstaller==6.16.0
if errorlevel 1 goto failed
".venv-build\Scripts\python.exe" validate.py
if errorlevel 1 goto failed
".venv-build\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onedir --console --collect-all pyspark --collect-all py4j --name IR_Search_Engine --add-data "templates;templates" --add-data "static;static" --add-data "data;data" launcher.py
if errorlevel 1 goto failed
echo The standalone build needs Java 17 or 21 on PATH for document imports.
echo Build complete: dist\IR_Search_Engine\IR_Search_Engine.exe
echo Distribute the ENTIRE IR_Search_Engine folder, including _internal.
pause
exit /b 0
:failed
echo Build failed. Review the output above. A Windows Python 3.12 installation is required.
pause
exit /b 1
