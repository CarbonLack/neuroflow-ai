param(
    [Parameter(Mandatory = $true)][string]$StandardAppDir,
    [Parameter(Mandatory = $true)][string]$FullAppDir,
    [Parameter(Mandatory = $true)][string]$OutputDir
)

$ErrorActionPreference = "Stop"
$standard = (Resolve-Path -LiteralPath $StandardAppDir).Path
$full = (Resolve-Path -LiteralPath $FullAppDir).Path
$output = [System.IO.Path]::GetFullPath($OutputDir)
if ($output -eq $standard -or $output -eq $full) {
    throw "Overlay output must not replace either application directory."
}
if (Test-Path -LiteralPath $output) {
    Remove-Item -LiteralPath $output -Recurse -Force
}
New-Item -ItemType Directory -Path $output | Out-Null

$standardFiles = @{}
Get-ChildItem -LiteralPath $standard -File -Recurse | ForEach-Object {
    $relative = $_.FullName.Substring($standard.Length + 1)
    $standardFiles[$relative] = $_
}

$manifest = New-Object System.Collections.Generic.List[object]
Get-ChildItem -LiteralPath $full -File -Recurse | ForEach-Object {
    $relative = $_.FullName.Substring($full.Length + 1)
    $reason = ""
    if (-not $standardFiles.ContainsKey($relative)) {
        $reason = "full-only"
    } else {
        $standardFile = $standardFiles[$relative]
        if ($standardFile.Length -ne $_.Length) {
            $reason = "changed-size"
        } else {
            $standardHash = (Get-FileHash -LiteralPath $standardFile.FullName -Algorithm SHA256).Hash
            $fullHash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
            if ($standardHash -ne $fullHash) {
                $reason = "changed-content"
            }
        }
    }
    if ($reason) {
        $destination = Join-Path $output $relative
        $destinationDir = Split-Path -Parent $destination
        if (-not (Test-Path -LiteralPath $destinationDir)) {
            New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
        }
        Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
        $manifest.Add([pscustomobject]@{
            relative_path = $relative
            bytes = $_.Length
            reason = $reason
        })
    }
}

$manifestPath = Join-Path $output "gpu_overlay_manifest.json"
$manifest | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $manifestPath -Encoding utf8
if (-not (Test-Path -LiteralPath (Join-Path $output "NeuroEphysAI.exe"))) {
    throw "Overlay is invalid: the Full executable does not differ from the Standard executable."
}
if (-not (Test-Path -LiteralPath (Join-Path $output "_internal\torch"))) {
    throw "Overlay is invalid: the torch payload is missing."
}
if (-not (Test-Path -LiteralPath (Join-Path $output "_internal\kilosort"))) {
    throw "Overlay is invalid: the Kilosort payload is missing."
}

$bytes = ($manifest | Measure-Object -Property bytes -Sum).Sum
Write-Host "GPU overlay created: $output"
Write-Host "Changed/full-only files: $($manifest.Count); bytes: $bytes"
