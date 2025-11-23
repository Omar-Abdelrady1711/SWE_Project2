@echo off
echo Starting Frontend Development Server...
echo.

cd /d "%~dp0Frontend"
call npm run dev

pause
