@echo off
cd /d "%~dp0"
echo This old bat had encoding issues on Chinese Windows CMD.
echo Please use: start-live.bat
echo.
pause
start "" "%~dp0start-live.bat"
