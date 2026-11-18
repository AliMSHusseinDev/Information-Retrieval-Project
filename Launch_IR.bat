@echo off
setlocal
cd /d "%~dp0"
if not exist "runtime\python\python.exe" goto source
set "JAVA_HOME=%~dp0runtime\java"
set "SPARK_HOME=%~dp0runtime\python\Lib\site-packages\pyspark"
set "PATH=%~dp0runtime\python;%JAVA_HOME%\bin;%PATH%"
set "PYSPARK_PYTHON=python"
set "SPARK_LOCAL_IP=127.0.0.1"
"runtime\python\python.exe" launcher.py
if errorlevel 1 goto failed
exit /b 0

:source
java -version || goto failed
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto failed
".venv\Scripts\python.exe" launcher.py
if errorlevel 1 goto failed
exit /b 0

:failed
echo Launch failed. See the console output and README.md.
pause
exit /b 1
