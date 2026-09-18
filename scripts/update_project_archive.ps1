param(
    [string]$SourceRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$ArchiveRoot = "D:\PhD\AI大赛\codex_neuroephys_ai",
    [string]$ReleaseStatus = "auto",
    [string]$TestSummary = "See 04_Analysis_and_Validation\01_Current_Release_QA\VALIDATION_REPORT.md"
)

$ErrorActionPreference = "Stop"
$source = (Resolve-Path -LiteralPath $SourceRoot).Path
$archive = [System.IO.Path]::GetFullPath($ArchiveRoot)
$productFile = Join-Path $source "neuroflow\product.py"
$productText = Get-Content -LiteralPath $productFile -Raw
$versionMatch = [regex]::Match($productText, 'PRODUCT_VERSION\s*=\s*"([^"]+)"')
if (-not $versionMatch.Success) {
    throw "Cannot read PRODUCT_VERSION from $productFile"
}

$version = $versionMatch.Groups[1].Value
$commit = (git -C $source rev-parse HEAD).Trim()
$branch = (git -C $source branch --show-current).Trim()
$remote = (git -C $source remote get-url origin).Trim()
$dirtyLines = @(git -C $source status --short)
$workingTree = if ($dirtyLines.Count -eq 0) { "clean" } else { "modified ($($dirtyLines.Count) item(s))" }
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
$releaseUrl = "https://github.com/CarbonLack/neuroflow-ai/releases/tag/v$version"
$exactTags = @(git -C $source tag --points-at HEAD)
if ($ReleaseStatus -eq "auto") {
    if ($exactTags -contains "v$version") { $ReleaseStatus = "released" }
    else { $ReleaseStatus = "development" }
}

$folders = @(
    "01_Source_Code",
    "02_Software_Releases",
    "02_Software_Releases\01_Latest_Release",
    "02_Software_Releases\02_Previous_Releases",
    "03_Data_and_Projects",
    "03_Data_and_Projects\01_Raw_Data",
    "03_Data_and_Projects\02_Example_Projects",
    "03_Data_and_Projects\03_Processed_Projects",
    "04_Analysis_and_Validation",
    "04_Analysis_and_Validation\01_Current_Release_QA",
    "04_Analysis_and_Validation\02_Simulated_Data_Validation",
    "04_Analysis_and_Validation\03_Real_Data_Validation",
    "04_Analysis_and_Validation\04_Sorter_Comparison",
    "05_Publication_Reproduction",
    "05_Publication_Reproduction\01_Trautmann_2025",
    "06_Documentation_and_Handover",
    "06_Documentation_and_Handover\01_User_Documentation",
    "06_Documentation_and_Handover\02_Developer_Documentation",
    "06_Documentation_and_Handover\03_Project_Handover",
    "07_Backup_Manifests",
    "07_Backup_Manifests\Legacy_Records"
)

New-Item -ItemType Directory -Path $archive -Force | Out-Null
foreach ($relative in $folders) {
    New-Item -ItemType Directory -Path (Join-Path $archive $relative) -Force | Out-Null
}

$readmeByFolder = [ordered]@{
    "." = @"
NEUROEPHYS AI - LIVING PROJECT ARCHIVE
======================================

This is the maintained, human-readable safeguard for the NeuroEphys AI project.
It is not a shortcut collection. Source snapshots, Git history, release notes,
validation reports, documentation, and manifests are stored here as real files.

Large raw datasets, processed projects, and multi-gigabyte installers remain in
their authoritative storage locations to avoid unsafe duplication on the nearly
full D: drive. Their exact locations and purposes are recorded in English index
files under 03_Data_and_Projects and 07_Backup_Manifests.

Start with CURRENT_STATUS.txt, then open the numbered folder you need.
The archive is refreshed automatically after Git commit, checkout, merge, and
release build operations. It can also be refreshed manually with:
scripts\update_project_archive.ps1
"@
    "01_Source_Code" = @"
SOURCE CODE BACKUP
==================

This folder contains two physical safeguards:
1. CURRENT_SOURCE_SNAPSHOT.zip - the exact tracked source tree at the recorded commit.
2. FULL_GIT_HISTORY.bundle - complete local Git history, branches, and tags.

Restore the current source by extracting the ZIP. Restore the repository history
with: git clone FULL_GIT_HISTORY.bundle neuroflow-ai
See SOURCE_VERSION.txt before restoring.
"@
    "02_Software_Releases" = @"
SOFTWARE RELEASES
=================

This folder documents the latest release and all known previous releases.
Large installers are not duplicated here because D: has limited free space.
The latest local and GitHub locations, file sizes, and checksums are recorded in
01_Latest_Release. Previous versions are indexed in 02_Previous_Releases.
"@
    "02_Software_Releases\01_Latest_Release" = @"
LATEST RELEASE
==============

Contains the current release notes, validation report, checksums, and exact download
or local-storage locations. Use the GitHub release for distribution. Use the local
E: archive only when rebuilding or validating the full offline package.
"@
    "02_Software_Releases\02_Previous_Releases" = @"
PREVIOUS RELEASES
=================

Contains an index of earlier release folders. These are retained for traceability,
regression investigation, and rollback decisions. They are not the recommended build.
"@
    "03_Data_and_Projects" = @"
DATA AND PROJECTS
=================

This section separates immutable raw data, generated example projects, and processed
analysis projects. The large payloads remain at their authoritative locations; this
archive stores English indexes so a new project manager can find them safely.
"@
    "03_Data_and_Projects\01_Raw_Data" = @"
RAW DATA
========

Original recordings and behavior files. Treat these locations as read-only evidence.
Do not overwrite, normalize, or delete raw files in place. Create a project under the
processed-project workspace and keep derived outputs separate.
"@
    "03_Data_and_Projects\02_Example_Projects" = @"
EXAMPLE PROJECTS
================

Generated benchmark and tutorial projects used for demonstrations, regression tests,
and end-to-end validation. See PROJECT_INDEX.csv for the authoritative workspace.
"@
    "03_Data_and_Projects\03_Processed_Projects" = @"
PROCESSED PROJECTS
==================

User-created projects, intermediate results, exported figures, tables, and audit logs.
These are derived products and must remain separate from immutable raw recordings.
"@
    "04_Analysis_and_Validation" = @"
ANALYSIS AND VALIDATION
=======================

Contains the current release acceptance evidence and indexes for simulated-data,
real-data, and sorter-comparison validation. Reports explain what ran, what failed,
what was fixed, and which outputs support each conclusion.
"@
    "04_Analysis_and_Validation\01_Current_Release_QA" = @"
CURRENT RELEASE QA
==================

The authoritative acceptance report for the current software version. Review this
before distributing an installer or claiming that a workflow is supported.
"@
    "04_Analysis_and_Validation\02_Simulated_Data_Validation" = @"
SIMULATED DATA VALIDATION
=========================

Indexes the two benchmark datasets and their end-to-end analysis evidence, including
import, preprocessing, sorting, unit QC, behavior alignment, figures, and exports.
"@
    "04_Analysis_and_Validation\03_Real_Data_Validation" = @"
REAL DATA VALIDATION
====================

Indexes validation performed on real recordings and behavior data. Raw inputs remain
outside this archive; reports and exact project locations are recorded here.
"@
    "04_Analysis_and_Validation\04_Sorter_Comparison" = @"
SORTER COMPARISON
=================

Indexes multi-sorter outputs, agreement analysis, quality metrics, and known runtime
constraints. A sorter is not considered supported merely because it is installed.
"@
    "05_Publication_Reproduction" = @"
PUBLICATION REPRODUCTION
========================

Contains reproducibility work based on public data and code. Each study has its own
folder with scope, source citation, status, outputs, and limitations.
"@
    "05_Publication_Reproduction\01_Trautmann_2025" = @"
TRAUTMANN 2025 REPRODUCTION
===========================

Reproduction workspace for Trautmann et al., Nature Neuroscience (2025), DOI:
10.1038/s41593-025-01976-5. See LOCATION_AND_STATUS.csv for the authoritative files.
"@
    "06_Documentation_and_Handover" = @"
DOCUMENTATION AND HANDOVER
==========================

User-facing instructions, developer references, release history, and project-manager
handover material. This section is designed to let another maintainer continue work
without relying on chat history.
"@
    "06_Documentation_and_Handover\01_User_Documentation" = @"
USER DOCUMENTATION
==================

Practical installation, workflow, AI assistant, and data-security guidance for users.
The published GitHub Pages site remains the primary public documentation.
"@
    "06_Documentation_and_Handover\02_Developer_Documentation" = @"
DEVELOPER DOCUMENTATION
=======================

Architecture, dependency, build, packaging, third-party attribution, and maintenance
references for developers and release engineers.
"@
    "06_Documentation_and_Handover\03_Project_Handover" = @"
PROJECT HANDOVER
================

Continuity material for the next project manager: project scope, decisions, completed
work, unresolved work, storage locations, release state, and operational cautions.
"@
    "07_Backup_Manifests" = @"
BACKUP MANIFESTS
================

Machine-readable inventories, external storage locations, checksums, and synchronization
history. Use these files to audit whether the living archive is current and complete.
"@
    "07_Backup_Manifests\Legacy_Records" = @"
LEGACY RECORDS
==============

Historical text records preserved during the one-time migration from the former Chinese
shortcut-based layout. These files are reference only and are not current status files.
"@
}

foreach ($entry in $readmeByFolder.GetEnumerator()) {
    $folderPath = if ($entry.Key -eq ".") { $archive } else { Join-Path $archive $entry.Key }
    Set-Content -LiteralPath (Join-Path $folderPath "README.txt") -Value $entry.Value.Trim() -Encoding UTF8
}

# Create real, restorable source backups rather than directory shortcuts.
$sourceFolder = Join-Path $archive "01_Source_Code"
$snapshotTarget = Join-Path $sourceFolder "CURRENT_SOURCE_SNAPSHOT.zip"
$bundleTarget = Join-Path $sourceFolder "FULL_GIT_HISTORY.bundle"
$snapshotTemp = "$snapshotTarget.tmp"
$bundleTemp = "$bundleTarget.tmp"
Remove-Item -LiteralPath $snapshotTemp, $bundleTemp -Force -ErrorAction SilentlyContinue
git -C $source archive --format=zip --output=$snapshotTemp HEAD
if ($LASTEXITCODE -ne 0) { throw "git archive failed" }
git -C $source bundle create $bundleTemp --all
if ($LASTEXITCODE -ne 0) { throw "git bundle creation failed" }
git -C $source bundle verify $bundleTemp | Out-Null
if ($LASTEXITCODE -ne 0) { throw "git bundle verification failed" }
Move-Item -LiteralPath $snapshotTemp -Destination $snapshotTarget -Force
Move-Item -LiteralPath $bundleTemp -Destination $bundleTarget -Force

$sourceVersion = @(
    "NeuroEphys AI source backup",
    "Version: v$version",
    "Branch: $branch",
    "Commit: $commit",
    "Working tree at refresh: $workingTree",
    "Remote: $remote",
    "Created: $timestamp",
    "",
    "CURRENT_SOURCE_SNAPSHOT.zip contains tracked files from the recorded commit.",
    "FULL_GIT_HISTORY.bundle contains the complete local Git history and tags.",
    "Uncommitted files are intentionally not represented as a restorable release."
) -join [Environment]::NewLine
Set-Content -LiteralPath (Join-Path $sourceFolder "SOURCE_VERSION.txt") -Value $sourceVersion -Encoding UTF8

# Copy compact release and documentation evidence as physical files.
$latestRelease = Join-Path $archive "02_Software_Releases\01_Latest_Release"
$qaFolder = Join-Path $archive "04_Analysis_and_Validation\01_Current_Release_QA"
$userDocs = Join-Path $archive "06_Documentation_and_Handover\01_User_Documentation"
$developerDocs = Join-Path $archive "06_Documentation_and_Handover\02_Developer_Documentation"
$handoverDocs = Join-Path $archive "06_Documentation_and_Handover\03_Project_Handover"

$copyPairs = @(
    @((Join-Path $source "RELEASE_NOTES_1.3.md"), (Join-Path $latestRelease "RELEASE_NOTES.md")),
    @((Join-Path $source "RELEASE_VALIDATION_1.3.md"), (Join-Path $latestRelease "VALIDATION_REPORT.md")),
    @((Join-Path $source "RELEASE_VALIDATION_1.3.md"), (Join-Path $qaFolder "VALIDATION_REPORT.md")),
    @((Join-Path $source "README.md"), (Join-Path $userDocs "GITHUB_README.md")),
    @((Join-Path $source "README_FIRST.md"), (Join-Path $userDocs "README_FIRST.md")),
    @((Join-Path $source "AI_USER_GUIDE_ZH.md"), (Join-Path $userDocs "AI_USER_GUIDE_ZH.md")),
    @((Join-Path $source "AI_DATA_SECURITY_ZH.md"), (Join-Path $userDocs "AI_DATA_SECURITY_ZH.md")),
    @((Join-Path $source "CHANGELOG.md"), (Join-Path $developerDocs "CHANGELOG.md")),
    @((Join-Path $source "THIRD_PARTY_SOURCES.md"), (Join-Path $developerDocs "THIRD_PARTY_SOURCES.md")),
    @((Join-Path $source "docs\PROJECT_ARCHIVE_SYNC_ZH.md"), (Join-Path $developerDocs "PROJECT_ARCHIVE_MAINTENANCE_ZH.md"))
)
foreach ($pair in $copyPairs) {
    if (Test-Path -LiteralPath $pair[0]) { Copy-Item -LiteralPath $pair[0] -Destination $pair[1] -Force }
}

$handoverSource = "D:\PhD\AI大赛\NeuroEphysAI_完整项目交接Prompt_20260916.md"
if (Test-Path -LiteralPath $handoverSource) {
    Copy-Item -LiteralPath $handoverSource -Destination (Join-Path $handoverDocs "PROJECT_HANDOVER_FULL_20260916.md") -Force
}

# Record heavyweight payloads by authoritative location instead of fragile shortcuts.
$externalRows = @(
    [pscustomobject]@{Category="Authoritative source repository"; Path=$source; Purpose="Active development and Git working tree"; Storage="D:"; IncludedPhysically="Snapshot and Git bundle"},
    [pscustomobject]@{Category="Local formal installations"; Path="D:\PhD\AI大赛\本地正式版"; Purpose="Installed application versions"; Storage="D:"; IncludedPhysically="No - indexed"},
    [pscustomobject]@{Category="Release validation"; Path="D:\PhD\AI大赛\发布验证"; Purpose="Installer and runtime QA workspaces"; Storage="D:"; IncludedPhysically="Reports only"},
    [pscustomobject]@{Category="Raw real data"; Path="D:\PhD\AI大赛\AI大赛"; Purpose="Original electrophysiology and behavior recordings"; Storage="D:"; IncludedPhysically="No - too large"},
    [pscustomobject]@{Category="Example projects"; Path="D:\PhD\AI大赛\NeuroEphysAI_Workspace"; Purpose="Simulated benchmarks and tutorial projects"; Storage="D:"; IncludedPhysically="No - too large"},
    [pscustomobject]@{Category="Current real-data validation"; Path="E:\NeuroEphysValidation"; Purpose="Processed real-data projects, results, figures, and logs"; Storage="E:"; IncludedPhysically="No - too large"},
    [pscustomobject]@{Category="Full release archive"; Path="E:\NeuroEphysAI_Archive\ReleaseBuilds\v$version"; Purpose="Full installer, portable package, GPU overlay, and validation installs"; Storage="E:"; IncludedPhysically="No - too large"},
    [pscustomobject]@{Category="Trautmann 2025 reproduction"; Path="D:\PhD\AI大赛\Trautmann2025_reproduction"; Purpose="Public-paper reproduction workspace"; Storage="D:"; IncludedPhysically="Status only"},
    [pscustomobject]@{Category="Historical independent documentation"; Path="D:\PhD\AI大赛\neuroephys-ai-docs"; Purpose="Earlier documentation repository"; Storage="D:"; IncludedPhysically="No - historical"},
    [pscustomobject]@{Category="Institutional AI harness workspace"; Path="D:\PhD\AI大赛\dswork"; Purpose="Official-harness integration workspace"; Storage="D:"; IncludedPhysically="No - separate system"}
)
foreach ($row in $externalRows) {
    $row | Add-Member -NotePropertyName Exists -NotePropertyValue (Test-Path -LiteralPath $row.Path)
}
$externalRows | Export-Csv -LiteralPath (Join-Path $archive "07_Backup_Manifests\EXTERNAL_LOCATIONS.csv") -NoTypeInformation -Encoding UTF8
$externalRows | Where-Object { $_.Category -eq "Raw real data" } | Export-Csv -LiteralPath (Join-Path $archive "03_Data_and_Projects\01_Raw_Data\DATASET_INDEX.csv") -NoTypeInformation -Encoding UTF8
$externalRows | Where-Object { $_.Category -eq "Example projects" } | Export-Csv -LiteralPath (Join-Path $archive "03_Data_and_Projects\02_Example_Projects\PROJECT_INDEX.csv") -NoTypeInformation -Encoding UTF8
$externalRows | Where-Object { $_.Category -eq "Current real-data validation" } | Export-Csv -LiteralPath (Join-Path $archive "03_Data_and_Projects\03_Processed_Projects\PROJECT_INDEX.csv") -NoTypeInformation -Encoding UTF8
$externalRows | Where-Object { $_.Category -eq "Example projects" } | Export-Csv -LiteralPath (Join-Path $archive "04_Analysis_and_Validation\02_Simulated_Data_Validation\LOCATION_INDEX.csv") -NoTypeInformation -Encoding UTF8
$externalRows | Where-Object { $_.Category -eq "Current real-data validation" } | Export-Csv -LiteralPath (Join-Path $archive "04_Analysis_and_Validation\03_Real_Data_Validation\LOCATION_INDEX.csv") -NoTypeInformation -Encoding UTF8
$externalRows | Where-Object { $_.Category -in @("Current real-data validation", "Example projects") } | Export-Csv -LiteralPath (Join-Path $archive "04_Analysis_and_Validation\04_Sorter_Comparison\LOCATION_INDEX.csv") -NoTypeInformation -Encoding UTF8
$externalRows | Where-Object { $_.Category -eq "Trautmann 2025 reproduction" } | Export-Csv -LiteralPath (Join-Path $archive "05_Publication_Reproduction\01_Trautmann_2025\LOCATION_AND_STATUS.csv") -NoTypeInformation -Encoding UTF8

$localReleaseRoot = "E:\NeuroEphysAI_Archive\ReleaseBuilds\v$version"
$assetRows = @()
if (Test-Path -LiteralPath $localReleaseRoot) {
    $assetRows = @(Get-ChildItem -LiteralPath $localReleaseRoot -File -Force | ForEach-Object {
        [pscustomobject]@{
            FileName = $_.Name
            FullPath = $_.FullName
            SizeBytes = $_.Length
            LastWriteTime = $_.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
            SHA256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    })
}
$assetRows | Export-Csv -LiteralPath (Join-Path $latestRelease "LOCAL_RELEASE_ASSETS.csv") -NoTypeInformation -Encoding UTF8

$previousRoot = Join-Path $source "release"
$previousRows = @()
if (Test-Path -LiteralPath $previousRoot) {
    $previousRows = @(Get-ChildItem -LiteralPath $previousRoot -Directory -Force | Sort-Object Name | ForEach-Object {
        [pscustomobject]@{Name=$_.Name; Path=$_.FullName; LastWriteTime=$_.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")}
    })
}
$previousRows | Export-Csv -LiteralPath (Join-Path $archive "02_Software_Releases\02_Previous_Releases\RELEASE_INDEX.csv") -NoTypeInformation -Encoding UTF8

$status = @(
    "NEUROEPHYS AI - CURRENT STATUS",
    "===============================",
    "",
    "Last archive refresh: $timestamp",
    "Current version: v$version",
    "Release status: $ReleaseStatus",
    "Git branch: $branch",
    "Git commit: $commit",
    "Working tree: $workingTree",
    "Tests: $TestSummary",
    "GitHub repository: $remote",
    "Current release: $releaseUrl",
    "",
    "Safeguard contents:",
    "- A real ZIP snapshot of the tracked source at this commit.",
    "- A verified Git bundle containing full local history and tags.",
    "- Physical copies of current release notes, QA evidence, and key documentation.",
    "- English indexes for large data, projects, releases, and validation workspaces.",
    "- No junctions, symbolic links, or Windows shortcut files inside this archive.",
    "",
    "Refresh rule: commit, checkout, merge, and release build hooks update this archive.",
    "Large files remain external because the D: drive has limited free space."
) -join [Environment]::NewLine
Set-Content -LiteralPath (Join-Path $archive "CURRENT_STATUS.txt") -Value $status -Encoding UTF8

$manifest = [ordered]@{
    archiveSchema = 2
    refreshedAt = $timestamp
    product = "NeuroEphys AI"
    version = $version
    releaseStatus = $ReleaseStatus
    branch = $branch
    commit = $commit
    workingTree = $workingTree
    sourceRepository = $source
    remote = $remote
    releaseUrl = $releaseUrl
    sourceSnapshot = "01_Source_Code/CURRENT_SOURCE_SNAPSHOT.zip"
    gitBundle = "01_Source_Code/FULL_GIT_HISTORY.bundle"
    externalLocationIndex = "07_Backup_Manifests/EXTERNAL_LOCATIONS.csv"
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $archive "SYNC_MANIFEST.json") -Encoding UTF8

$inventoryPath = Join-Path $archive "07_Backup_Manifests\ARCHIVE_FILE_INVENTORY.csv"
$inventoryRows = @(Get-ChildItem -LiteralPath $archive -File -Recurse -Force | Where-Object { $_.FullName -ne $inventoryPath } | Sort-Object FullName | ForEach-Object {
    [pscustomobject]@{
        RelativePath = $_.FullName.Substring($archive.Length).TrimStart('\')
        SizeBytes = $_.Length
        LastWriteTime = $_.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
        SHA256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    }
})
$inventoryRows | Export-Csv -LiteralPath $inventoryPath -NoTypeInformation -Encoding UTF8

$historyPath = Join-Path $archive "07_Backup_Manifests\SYNC_HISTORY.log"
$historyLine = "$timestamp | v$version | $commit | $ReleaseStatus | $workingTree"
$lastHistoryLine = if (Test-Path -LiteralPath $historyPath) { Get-Content -LiteralPath $historyPath -Tail 1 } else { "" }
if ($lastHistoryLine -ne $historyLine) { Add-Content -LiteralPath $historyPath -Value $historyLine -Encoding UTF8 }

Write-Host "Updated living project archive: $archive"
Write-Host "Version: v$version"
Write-Host "Commit: $commit"
Write-Host "Source snapshot: $snapshotTarget"
Write-Host "Git history bundle: $bundleTarget"
