param(
    [switch]$SkipTests,
    [switch]$SkipDocs,
    [string]$ReleaseRoot,
    [string]$BuildRoot,
    [string]$DistRoot
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$BuildScript = Join-Path $PSScriptRoot "build_release.ps1"
$OverlayScript = Join-Path $PSScriptRoot "make_gpu_overlay.ps1"
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "The managed Python environment is missing: $Python"
}
$Version = (& $Python -c "from neuroflow.product import PRODUCT_VERSION; print(PRODUCT_VERSION)").Trim()
$ReleaseRoot = if ($ReleaseRoot) { [System.IO.Path]::GetFullPath($ReleaseRoot) } else { [System.IO.Path]::GetFullPath((Join-Path $Root "release")) }
$BuildRoot = if ($BuildRoot) { [System.IO.Path]::GetFullPath($BuildRoot) } else { [System.IO.Path]::GetFullPath((Join-Path $Root "build")) }
$DistRoot = if ($DistRoot) { [System.IO.Path]::GetFullPath($DistRoot) } else { [System.IO.Path]::GetFullPath((Join-Path $Root "dist")) }
$ReleaseDir = [System.IO.Path]::GetFullPath((Join-Path $ReleaseRoot "v$Version"))
$Staging = [System.IO.Path]::GetFullPath((Join-Path $BuildRoot "dual-release-v$Version"))
if (-not $Staging.StartsWith($BuildRoot + [System.IO.Path]::DirectorySeparatorChar)) {
    throw "Refusing to use an unsafe staging directory: $Staging"
}
if (Test-Path -LiteralPath $Staging) {
    Remove-Item -LiteralPath $Staging -Recurse -Force
}
New-Item -ItemType Directory -Path $Staging | Out-Null

try {
    $CoreParams = @{ Lite = $true; ReleaseRoot = $ReleaseRoot; DistRoot = $DistRoot; WorkRoot = (Join-Path $BuildRoot "pyinstaller-standard") }
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

    $StandardApp = Join-Path $Staging "standard-app"
    $BuiltApp = Join-Path $DistRoot "NeuroEphysAI"
    if (-not (Test-Path -LiteralPath $BuiltApp)) {
        throw "Validated Standard application directory is missing: $BuiltApp"
    }
    Move-Item -LiteralPath $BuiltApp -Destination $StandardApp

    $FullParams = @{ SkipTests = $true; SkipDocs = $true; SkipInstaller = $true; ReleaseRoot = $ReleaseRoot; DistRoot = $DistRoot; WorkRoot = (Join-Path $BuildRoot "pyinstaller-full") }
    & $BuildScript @FullParams
    if ($LASTEXITCODE -ne 0) {
        throw "Full offline release build failed with exit code $LASTEXITCODE."
    }

    $FullApp = Join-Path $DistRoot "NeuroEphysAI"
    $GpuOverlay = Join-Path $Staging "gpu-overlay"
    & $OverlayScript `
        -StandardAppDir $StandardApp `
        -FullAppDir $FullApp `
        -OutputDir $GpuOverlay
    if ($LASTEXITCODE -ne 0) {
        throw "GPU overlay generation failed with exit code $LASTEXITCODE."
    }

    $InnoCandidates = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    $InnoCompiler = $InnoCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $InnoCompiler) {
        throw "Inno Setup 6 is required to build the selectable Full installer."
    }
    & $InnoCompiler `
        "/DMyAppVersion=$Version" `
        "/DFullBuild=1" `
        "/DCoreAppDir=$StandardApp" `
        "/DGpuOverlayDir=$GpuOverlay" `
        "/O$ReleaseDir" `
        "/FNeuroEphysAI-Setup-$Version-Full" `
        (Join-Path $Root "installer\NeuroEphysAI.iss")
    if ($LASTEXITCODE -ne 0) {
        throw "Selectable Full installer build failed with exit code $LASTEXITCODE."
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
