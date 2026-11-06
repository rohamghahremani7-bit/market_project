@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".env" (
  echo [ERROR] .env not found. Run setup.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
pause
