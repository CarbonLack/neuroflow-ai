param(
    [string]$WorkspaceRoot = (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)))
)

$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath($WorkspaceRoot)
$repo = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$expected = [System.IO.Path]::GetFullPath((Join-Path $root '02_Source_Code\Repository'))
if ($repo -ne $expected -or -not (Test-Path -LiteralPath (Join-Path $root '00_START_HERE\README.txt'))) {
    throw 'This script must run from the canonical codex_neuroephys_ai workspace.'
}

$sourceFolder = Join-Path $root '02_Source_Code'
$bundle = Join-Path $sourceFolder 'FULL_GIT_HISTORY.bundle'
$temporary = Join-Path $sourceFolder 'FULL_GIT_HISTORY.bundle.tmp'
if (Test-Path -LiteralPath $temporary) {
    Remove-Item -LiteralPath $temporary -Force
}
& git -C $repo bundle create $temporary --all
if ($LASTEXITCODE -ne 0) { throw 'Could not create the Git recovery bundle.' }
& git -C $repo bundle verify $temporary | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'The Git recovery bundle failed verification.' }
Move-Item -LiteralPath $temporary -Destination $bundle -Force

$productText = Get-Content -LiteralPath (Join-Path $repo 'neuroflow\product.py') -Raw
$match = [regex]::Match($productText, 'PRODUCT_VERSION\s*=\s*"([^"]+)"')
if (-not $match.Success) { throw 'Cannot read the product version.' }
$version = $match.Groups[1].Value
$commit = (& git -C $repo rev-parse HEAD).Trim()
$status = @(& git -C $repo status --short)
$release = Join-Path $root "01_Application\Releases\v$version"
$record = @(
    'PORTABLE WORKSPACE CURRENT STATE',
    "Updated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')",
    "Version: $version",
    "Git commit: $commit",
    "Working tree: $(if ($status.Count) { 'modified' } else { 'clean' })",
    "Runnable App: 01_Application\Full_Portable\NeuroEphysAI.exe",
    "Release set: 01_Application\Releases\v$version",
    "Release set exists: $(Test-Path -LiteralPath $release)",
    'Source: 02_Source_Code\Repository',
    'Offline source recovery: 02_Source_Code\FULL_GIT_HISTORY.bundle',
    'User and example data: 03_Example_Projects and 04_User_Projects',
    'External research-data collections are inventoried in 05_Research_Data_Catalog.'
)
$record | Set-Content -LiteralPath (Join-Path $root '08_Manifests_and_Recovery\CURRENT_WORKSPACE_STATE.txt') -Encoding utf8
Write-Host "Portable workspace recovery bundle refreshed for v$version ($commit)."
