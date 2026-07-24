$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Run scripts\setup_windows.ps1 before building."
}

Push-Location $Root
try {
    & $Python -m pip install "pyinstaller>=6.10,<7"
    & $Python -m PyInstaller --noconfirm --clean NeuroFlow.spec
    Write-Host "Portable application created at dist\NeuroFlow\NeuroFlow.exe" -ForegroundColor Green
} finally {
    Pop-Location
}
