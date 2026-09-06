@echo off
cd /d "%~dp0"
echo ========================================
echo  VR / PSP LIVE board
echo ========================================
echo.
where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] python not found.
  echo Install Python 3 and check "Add python.exe to PATH"
  echo https://www.python.org/downloads/
  pause
  exit /b 1
)
echo Starting live website...
echo Keep this window OPEN. Browser will open automatically.
echo Close this window = stop auto update.
echo.
python scripts\live_site.py --interval 45
echo.
echo Stopped.
pause
