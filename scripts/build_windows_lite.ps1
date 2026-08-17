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
    $env:NEUROEPHYS_LITE_BUILD = "1"
    & $Python -m PyInstaller --noconfirm --clean NeuroFlow.spec
    if ($LASTEXITCODE -ne 0) {
        throw "NeuroEphys AI core packaging failed with exit code $LASTEXITCODE."
    }
    Write-Host "Core application created at dist\NeuroEphysAI\NeuroEphysAI.exe" -ForegroundColor Green
    Write-Host "Kilosort/CUDA remains available through the managed full analysis environment." -ForegroundColor Yellow
} finally {
    Remove-Item Env:NEUROEPHYS_LITE_BUILD -ErrorAction SilentlyContinue
    Pop-Location
}
