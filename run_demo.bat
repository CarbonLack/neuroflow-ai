@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" app.py
) else if exist "..\.venv312\Scripts\pythonw.exe" (
  start "" "..\.venv312\Scripts\pythonw.exe" app.py
) else (
  echo NeuroFlow environment is not installed.
  echo Run: powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
  pause
)
endlocal
