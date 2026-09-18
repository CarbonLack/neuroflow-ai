param(
    [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$Launch
)

$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath($WorkspaceRoot).TrimEnd('\')
$expectedName = 'codex_neuroephys_ai'
if ((Split-Path -Leaf $root) -ne $expectedName) {
    throw "Expected the portable workspace root to be named '$expectedName': $root"
}

$projectRoot = Join-Path $root '03_Example_Projects'
$manifests = @(Get-ChildItem -LiteralPath $projectRoot -Filter 'neuroflow_project.json' -File -Recurse)
$updated = 0
$statePath = Join-Path $root '08_Manifests_and_Recovery\PORTABILITY_STATE.json'
$alreadyPrepared = $false
if (Test-Path -LiteralPath $statePath -PathType Leaf) {
    try {
        $previous = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $alreadyPrepared = [string]$previous.workspace_root -eq $root
    } catch {
        $alreadyPrepared = $false
    }
}

foreach ($manifest in $(if ($alreadyPrepared) { @() } else { $manifests })) {
    $project = $manifest.Directory.FullName
    $rawDir = Join-Path $project 'raw'
    $recording = $null
    foreach ($name in @('recording.bin', 'neuroflow_simulated_recording.bin')) {
        $candidate = Join-Path $rawDir $name
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            $recording = $candidate
            break
        }
    }
    if ($recording) {
        $jsonPath = $recording.Replace('\', '\\')
        $text = Get-Content -LiteralPath $manifest.FullName -Raw -Encoding UTF8
        $text = [regex]::Replace(
            $text,
            '(?m)^\s*"source_path"\s*:\s*"[^"]*"',
            '  "source_path": "' + $jsonPath + '"',
            1
        )
        $text = [regex]::Replace(
            $text,
            '(?m)^\s*"recording_path"\s*:\s*"[^"]*"',
            '  "recording_path": "' + $jsonPath + '"',
            1
        )
        Set-Content -LiteralPath $manifest.FullName -Value $text -Encoding UTF8
        $updated++
    }
}

$state = [ordered]@{
    prepared_at = (Get-Date).ToString('o')
    workspace_root = $root
    project_manifests = $manifests.Count
    rebound_manifests = $updated
}
$state | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8

Write-Host "Portable workspace prepared: $root"
Write-Host "Project manifests checked: $($manifests.Count)"

if ($Launch) {
    $app = Join-Path $root '01_Application\Full_Portable\NeuroEphysAI.exe'
    if (-not (Test-Path -LiteralPath $app -PathType Leaf)) {
        throw "Application not found: $app"
    }
    Start-Process -FilePath $app -WorkingDirectory (Split-Path -Parent $app)
}
