param(
    [switch]$SkipTests,
    [switch]$SkipDocs,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $VenvPython) {
    $Python = $VenvPython
} else {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonCommand) {
        throw "Python 3.12 is required to build a release."
    }
    $Python = $PythonCommand.Source
    $PythonVersion = (& $Python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
    if ($PythonVersion -ne "3.12") {
        throw "Python 3.12 is required to build a release; found $PythonVersion."
    }
}

Push-Location $Root
try {
    $Version = (& $Python -c "from neuroflow.product import PRODUCT_VERSION; print(PRODUCT_VERSION)").Trim()
    if ($Version -notmatch '^\d+\.\d+\.\d+$') {
        throw "Invalid release version: $Version"
    }
    $ReleaseRoot = Join-Path $Root "release"
    $ReleaseDir = Join-Path $ReleaseRoot "v$Version"
    $ResolvedReleaseRoot = [System.IO.Path]::GetFullPath($ReleaseRoot)
    $ResolvedReleaseDir = [System.IO.Path]::GetFullPath($ReleaseDir)
    if (-not $ResolvedReleaseDir.StartsWith($ResolvedReleaseRoot + [System.IO.Path]::DirectorySeparatorChar)) {
        throw "Refusing to clean an invalid release path: $ResolvedReleaseDir"
    }
    if (Test-Path -LiteralPath $ResolvedReleaseDir) {
        Remove-Item -LiteralPath $ResolvedReleaseDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $ResolvedReleaseDir | Out-Null

    & $Python -m pip install "pyinstaller>=6.10,<7" "build>=1.2,<2" "twine>=6,<7"
    if ($LASTEXITCODE -ne 0) {
        throw "Release tooling installation failed with exit code $LASTEXITCODE."
    }

    if (-not $SkipTests) {
        $env:QT_QPA_PLATFORM = "offscreen"
        & $Python -m pytest -q
        if ($LASTEXITCODE -ne 0) {
            throw "Automated tests failed with exit code $LASTEXITCODE."
        }
    }

    if (-not $SkipDocs) {
        & $Python -m pip install -r (Join-Path $Root "docs\requirements.txt")
        if ($LASTEXITCODE -ne 0) {
            throw "Documentation dependencies failed with exit code $LASTEXITCODE."
        }
        & $Python (Join-Path $Root "scripts\build_sphinx_docs.py")
        if ($LASTEXITCODE -ne 0) {
            throw "Documentation build failed with exit code $LASTEXITCODE."
        }
    }

    $env:NEUROEPHYS_LITE_BUILD = "1"
    & $Python -m PyInstaller --noconfirm --clean (Join-Path $Root "NeuroFlow.spec")
    if ($LASTEXITCODE -ne 0) {
        throw "Windows application build failed with exit code $LASTEXITCODE."
    }
    Remove-Item Env:NEUROEPHYS_LITE_BUILD -ErrorAction SilentlyContinue

    $AppDir = Join-Path $Root "dist\NeuroEphysAI"
    $AppExe = Join-Path $AppDir "NeuroEphysAI.exe"
    if (-not (Test-Path -LiteralPath $AppExe)) {
        throw "The packaged executable was not created: $AppExe"
    }

    $VerificationDir = Join-Path $ResolvedReleaseDir "verification"
    New-Item -ItemType Directory -Path $VerificationDir | Out-Null
    $env:NEUROEPHYS_HOME = $VerificationDir
    $StartupSelfTest = Start-Process -FilePath $AppExe -ArgumentList "--self-test-startup" -PassThru -Wait -WindowStyle Hidden
    if ($StartupSelfTest.ExitCode -ne 0) {
        throw "Packaged startup self-test failed with exit code $($StartupSelfTest.ExitCode)."
    }
    $AiSelfTest = Start-Process -FilePath $AppExe -ArgumentList "--self-test-ai" -PassThru -Wait -WindowStyle Hidden
    if ($AiSelfTest.ExitCode -ne 0) {
        throw "Packaged AI self-test failed with exit code $($AiSelfTest.ExitCode)."
    }
    $FigureSelfTest = Start-Process -FilePath $AppExe -ArgumentList "--self-test-figure-export" -PassThru -Wait -WindowStyle Hidden
    if ($FigureSelfTest.ExitCode -ne 0) {
        throw "Packaged figure self-test failed with exit code $($FigureSelfTest.ExitCode)."
    }
    Remove-Item Env:NEUROEPHYS_HOME -ErrorAction SilentlyContinue

    $PortableZip = Join-Path $ResolvedReleaseDir "NeuroEphysAI-$Version-Windows-x64-portable.zip"
    # The native archive tool tolerates short-lived antivirus/indexer handles
    # more reliably than Compress-Archive for a large scientific one-folder app.
    & tar.exe -a -c -f $PortableZip -C (Join-Path $Root "dist") "NeuroEphysAI"
    if ($LASTEXITCODE -ne 0) {
        throw "Portable archive creation failed with exit code $LASTEXITCODE."
    }

    & $Python -m build --outdir $ResolvedReleaseDir
    if ($LASTEXITCODE -ne 0) {
        throw "Python package build failed with exit code $LASTEXITCODE."
    }
    $PythonArtifacts = Get-ChildItem -LiteralPath $ResolvedReleaseDir -File |
        Where-Object { $_.Name -like "neuroephys_ai-$Version*" }
    & $Python -m twine check $PythonArtifacts.FullName
    if ($LASTEXITCODE -ne 0) {
        throw "Python distribution metadata validation failed with exit code $LASTEXITCODE."
    }

    if (-not $SkipInstaller) {
        $InnoCandidates = @(
            "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
        )
        $InnoCompiler = $InnoCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        if (-not $InnoCompiler) {
            throw "Inno Setup 6 is required to build the installer. Use -SkipInstaller only for diagnostics."
        }
        & $InnoCompiler "/DMyAppVersion=$Version" "/O$ResolvedReleaseDir" "/FNeuroEphysAI-Setup-$Version" (Join-Path $Root "installer\NeuroEphysAI.iss")
        if ($LASTEXITCODE -ne 0) {
            throw "Installer build failed with exit code $LASTEXITCODE."
        }
    }

    foreach ($ReleaseDocument in @(
        "README_FIRST.md",
        "RELEASE_NOTES_1.0.md",
        "RELEASE_VALIDATION_1.0.md"
    )) {
        $SourceDocument = Join-Path $Root $ReleaseDocument
        if (-not (Test-Path -LiteralPath $SourceDocument)) {
            throw "Required release document is missing: $SourceDocument"
        }
        Copy-Item -LiteralPath $SourceDocument -Destination $ResolvedReleaseDir -Force
    }

    $VerificationArchive = Join-Path $ResolvedReleaseDir "verification"
    if (Test-Path -LiteralPath $VerificationArchive) {
        Remove-Item -LiteralPath $VerificationArchive -Recurse -Force
    }
    $Artifacts = Get-ChildItem -LiteralPath $ResolvedReleaseDir -File | Sort-Object Name
    $HashLines = foreach ($Artifact in $Artifacts) {
        $Hash = (Get-FileHash -LiteralPath $Artifact.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        "$Hash  $($Artifact.Name)"
    }
    $HashLines | Set-Content -LiteralPath (Join-Path $ResolvedReleaseDir "SHA256SUMS.txt") -Encoding utf8

    Write-Host "NeuroEphys AI $Version release created at $ResolvedReleaseDir" -ForegroundColor Green
    Get-ChildItem -LiteralPath $ResolvedReleaseDir -File | Select-Object Name, Length
} finally {
    Remove-Item Env:NEUROEPHYS_LITE_BUILD -ErrorAction SilentlyContinue
    Remove-Item Env:NEUROEPHYS_HOME -ErrorAction SilentlyContinue
    Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
    Pop-Location
}
