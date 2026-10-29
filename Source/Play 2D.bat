@echo off
rem Double-click to play. The first run installs the libraries (needs internet, about 1-3 minutes).
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 main.py
) else (
    where python >nul 2>nul || goto nopython
    python main.py
)
if errorlevel 1 pause
exit /b

:nopython
echo Python 3 is not installed. Get it from https://www.python.org/downloads/ (tick "Add python.exe to PATH").
pause
