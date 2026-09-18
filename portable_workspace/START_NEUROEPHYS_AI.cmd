@echo off
setlocal
set "WORKSPACE_ROOT=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%WORKSPACE_ROOT%08_Manifests_and_Recovery\Prepare_Portable_Workspace.ps1" -WorkspaceRoot "%WORKSPACE_ROOT%" -Launch
if errorlevel 1 (
  echo.
  echo Workspace preparation or launch failed. See 00_START_HERE\README.txt.
  pause
)
endlocal
