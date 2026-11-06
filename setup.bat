@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Python virtual environment .venv not found.
  echo Open this project in VS Code and create/activate the environment first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" setup_project.py
if errorlevel 1 echo Setup failed. Review the message above.
pause
