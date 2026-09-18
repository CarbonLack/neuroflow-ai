param(
    [Parameter(Mandatory = $true)][string]$WorkspaceRoot,
    [string]$ExpectedCsv = '',
    [string]$OutputCsv = ''
)

$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath($WorkspaceRoot).TrimEnd('\')
$manifestDir = Join-Path $root '08_Manifests_and_Recovery'
if (-not $ExpectedCsv) {
    $ExpectedCsv = Join-Path $manifestDir 'BENCHMARK_RECORDING_SHA256.csv'
}
if (-not $OutputCsv) {
    $OutputCsv = Join-Path $manifestDir 'FINAL_RECORDING_SHA256.csv'
}

$benchmarkRoot = Join-Path $root '03_Example_Projects\Standard_Benchmark_20min_v2'
$expected = Import-Csv -LiteralPath $ExpectedCsv
$results = @()
foreach ($row in $expected) {
    $recording = Join-Path $benchmarkRoot $row.RelativePath
    if (-not (Test-Path -LiteralPath $recording -PathType Leaf)) {
        throw "Missing benchmark recording: $recording"
    }
    $hash = (Get-FileHash -LiteralPath $recording -Algorithm SHA256).Hash
    $results += [pscustomobject]@{
        RelativePath = $row.RelativePath
        Bytes = (Get-Item -LiteralPath $recording).Length
        ExpectedSHA256 = $row.SourceSHA256
        ActualSHA256 = $hash
        Match = $row.SourceSHA256 -eq $hash
    }
}
$results | Export-Csv -LiteralPath $OutputCsv -NoTypeInformation -Encoding UTF8
$mismatches = @($results | Where-Object { -not $_.Match })
Write-Host "Verified $($results.Count) benchmark recordings; mismatches: $($mismatches.Count)"
if ($mismatches.Count) {
    exit 2
}
