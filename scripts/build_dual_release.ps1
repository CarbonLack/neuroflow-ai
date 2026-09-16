param(
    [switch]$SkipTests,
    [switch]$SkipDocs
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$BuildScript = Join-Path $PSScriptRoot "build_release.ps1"
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "The managed Python environment is missing: $Python"
}
$Version = (& $Python -c "from neuroflow.product import PRODUCT_VERSION; print(PRODUCT_VERSION)").Trim()
$ReleaseDir = [System.IO.Path]::GetFullPath((Join-Path $Root "release\v$Version"))
$BuildRoot = [System.IO.Path]::GetFullPath((Join-Path $Root "build"))
$Staging = [System.IO.Path]::GetFullPath((Join-Path $BuildRoot "dual-release-v$Version"))
if (-not $Staging.StartsWith($BuildRoot + [System.IO.Path]::DirectorySeparatorChar)) {
    throw "Refusing to use an unsafe staging directory: $Staging"
}
if (Test-Path -LiteralPath $Staging) {
    Remove-Item -LiteralPath $Staging -Recurse -Force
}
New-Item -ItemType Directory -Path $Staging | Out-Null

try {
    $CoreParams = @{ Lite = $true }
    if ($SkipTests) { $CoreParams.SkipTests = $true }
    if ($SkipDocs) { $CoreParams.SkipDocs = $true }
    & $BuildScript @CoreParams
    if ($LASTEXITCODE -ne 0) {
        throw "Standard release build failed with exit code $LASTEXITCODE."
    }
    foreach ($Name in @(
        "NeuroEphysAI-Setup-$Version.exe",
        "NeuroEphysAI-$Version-Windows-x64-portable.zip"
    )) {
        $Source = Join-Path $ReleaseDir $Name
        if (-not (Test-Path -LiteralPath $Source)) {
            throw "Standard artifact is missing: $Source"
        }
        Copy-Item -LiteralPath $Source -Destination $Staging -Force
    }

    $FullParams = @{ SkipTests = $true; SkipDocs = $true }
    & $BuildScript @FullParams
    if ($LASTEXITCODE -ne 0) {
        throw "Full offline release build failed with exit code $LASTEXITCODE."
    }
    Get-ChildItem -LiteralPath $Staging -File | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $ReleaseDir -Force
    }

    $HashPath = Join-Path $ReleaseDir "SHA256SUMS.txt"
    $HashLines = Get-ChildItem -LiteralPath $ReleaseDir -File |
        Where-Object { $_.Name -ne "SHA256SUMS.txt" } |
        Sort-Object Name |
        ForEach-Object {
            $Hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            "$Hash  $($_.Name)"
        }
    $HashLines | Set-Content -LiteralPath $HashPath -Encoding utf8
    Write-Host "Standard and Full offline artifacts are ready at $ReleaseDir" -ForegroundColor Green
    Get-ChildItem -LiteralPath $ReleaseDir -File | Select-Object Name, Length
} finally {
    if (Test-Path -LiteralPath $Staging) {
        Remove-Item -LiteralPath $Staging -Recurse -Force
    }
}
