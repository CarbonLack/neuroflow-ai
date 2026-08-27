param(
    [string]$TorchIndexUrl = "https://download.pytorch.org/whl/cu128"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Run scripts\setup_windows.ps1 first so the NeuroEphys AI Python 3.12 environment exists."
}

Push-Location $Root
try {
    Write-Host "Installing the CUDA-enabled PyTorch runtime for Kilosort4..." -ForegroundColor Cyan
    & $Python -m pip install "torch==2.11.0" --index-url $TorchIndexUrl
    if ($LASTEXITCODE -ne 0) {
        throw "PyTorch CUDA installation failed with exit code $LASTEXITCODE."
    }
    Write-Host "Installing every sorter in the curated NeuroEphys AI catalog..." -ForegroundColor Cyan
    & $Python -m pip install -e ".[full]"
    if ($LASTEXITCODE -ne 0) {
        throw "Sorter installation failed with exit code $LASTEXITCODE."
    }
    & $Python -c "import json; from neuroflow.sorting import refresh_sorter_catalog, kilosort_environment; print(json.dumps({'sorters': refresh_sorter_catalog(), 'kilosort': kilosort_environment()}, ensure_ascii=False, indent=2))"
    if ($LASTEXITCODE -ne 0) {
        throw "Sorter verification failed with exit code $LASTEXITCODE."
    }
    Write-Host "All six supported NeuroEphys AI sorters are installed and have been probed." -ForegroundColor Green
} finally {
    Pop-Location
}
