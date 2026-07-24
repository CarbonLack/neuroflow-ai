$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $DevelopmentPython = Join-Path (Split-Path -Parent $Root) ".venv312\Scripts\python.exe"
    if (Test-Path $DevelopmentPython) {
        $Python = $DevelopmentPython
    } else {
        throw "Run scripts\setup_windows.ps1 before building."
    }
}

Push-Location $Root
try {
    & $Python -m pip install "pyinstaller>=6.10,<7"
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller installation failed with exit code $LASTEXITCODE."
    }
    & $Python -m PyInstaller --noconfirm --clean NeuroFlow.spec
    if ($LASTEXITCODE -ne 0) {
        throw "NeuroFlow packaging failed with exit code $LASTEXITCODE."
    }
    Write-Host "Portable application created at dist\NeuroFlow\NeuroFlow.exe" -ForegroundColor Green
} finally {
    Pop-Location
}
