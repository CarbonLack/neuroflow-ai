@echo off
setlocal
cd /d "%~dp0"
if exist "..\.venv312\Scripts\pythonw.exe" (
  start "" "..\.venv312\Scripts\pythonw.exe" app.py
) else (
  pythonw app.py
)
endlocal
