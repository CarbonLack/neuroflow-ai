$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root ".venv"

Write-Host "NeuroFlow Windows setup" -ForegroundColor Cyan
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python 3.12 is required. Install it from python.org, then run this script again."
}
if (-not (Test-Path $Venv)) {
    py -3.12 -m venv $Venv
}
$Python = Join-Path $Venv "Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Root "requirements.txt")
& $Python -m pytest -q (Join-Path $Root "tests")

Write-Host ""
Write-Host "Setup completed. Double-click run_demo.bat." -ForegroundColor Green
Write-Host "Kilosort4 will use CUDA only when a compatible NVIDIA driver and PyTorch CUDA build are available."
