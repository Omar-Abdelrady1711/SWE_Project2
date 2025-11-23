@echo off
echo Starting FastAPI Backend...
echo.
echo Make sure you have activated your virtual environment first!
echo If not, run: .venv\Scripts\activate
echo.

cd /d "%~dp0"
python -m uvicorn bs.src.app:app --reload --host 0.0.0.0 --port 8000

pause
