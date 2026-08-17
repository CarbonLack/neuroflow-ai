$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root ".venv"

Write-Host "NeuroEphys AI development environment setup" -ForegroundColor Cyan
if (-not (Test-Path $Venv)) {
    $Python312 = $null
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $Python312 = @("py", "-3.12")
        }
    }
    if (-not $Python312) {
        foreach ($Candidate in @("python3.12", "python")) {
            if (Get-Command $Candidate -ErrorAction SilentlyContinue) {
                & $Candidate -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" 2>$null
                if ($LASTEXITCODE -eq 0) {
                    $Python312 = @($Candidate)
                    break
                }
            }
        }
    }
    if (-not $Python312) {
        throw "Python 3.12 is required for source development. App users should use the installer and do not need Python."
    }
    if ($Python312.Count -eq 2) {
        & $Python312[0] $Python312[1] -m venv $Venv
    } else {
        & $Python312[0] -m venv $Venv
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Creating the Python 3.12 virtual environment failed."
    }
}
$Python = Join-Path $Venv "Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Root "requirements.txt")
& $Python -m pytest -q (Join-Path $Root "tests")

Write-Host ""
Write-Host "Setup completed. Run the source app with .venv\Scripts\python.exe app.py." -ForegroundColor Green
Write-Host "Kilosort4 will use CUDA only when a compatible NVIDIA driver and PyTorch CUDA build are available."
