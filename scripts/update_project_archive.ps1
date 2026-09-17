param(
    [string]$SourceRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$ArchiveRoot = "D:\PhD\AI大赛\codex_neuroephys_ai",
    [string]$ReleaseStatus = "development",
    [string]$TestSummary = "not supplied"
)

$ErrorActionPreference = "Stop"
$source = (Resolve-Path -LiteralPath $SourceRoot).Path
if (-not (Test-Path -LiteralPath $ArchiveRoot)) {
    Write-Host "Project archive is not present on this computer; snapshot refresh skipped: $ArchiveRoot"
    exit 0
}
$archive = (Resolve-Path -LiteralPath $ArchiveRoot).Path
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

$snapshot = @(
    "NeuroEphys AI 项目动态快照",
    "===========================",
    "",
    "更新时间：$timestamp",
    "当前版本：v$version",
    "发布状态：$ReleaseStatus",
    "Git 分支：$branch",
    "Git 提交：$commit",
    "工作区：$workingTree",
    "测试：$TestSummary",
    "",
    "权威源代码：$source",
    "GitHub：$remote",
    "当前版本发布页：$releaseUrl",
    "",
    "目录说明：",
    "- 01_源代码\neuroflow-ai 是指向权威仓库的目录链接，源码变化会立即反映。",
    "- 02_软件发布 指向安装版、仓库发布产物和独立发布验证。",
    "- 03_数据与项目 指向原始数据、模拟项目和真实数据项目；不重复占用空间。",
    "- 04_分析与验证 指向可审阅结果、图、表和日志。",
    "- 05_论文复现 指向公开论文复现工作。",
    "- 06_文档与交接 保存总览、历史与交接入口。",
    "",
    "维护规则：本地 Git 提交/切换/合并由 .githooks 自动刷新；版本打包由",
    "scripts\build_release.ps1 自动刷新；GitHub Release 完成后再写入 released 状态。",
    "如需手工核对，可运行 scripts\update_project_archive.ps1。"
) -join [Environment]::NewLine

$snapshotPath = Join-Path $archive "项目动态快照.txt"
Set-Content -LiteralPath $snapshotPath -Value $snapshot -Encoding UTF8

$changeSource = Join-Path $source "RELEASE_NOTES_1.3.md"
$changeTarget = Join-Path $archive "06_文档与交接\当前版本变化.md"
Copy-Item -LiteralPath $changeSource -Destination $changeTarget -Force

$validationSource = Join-Path $source "RELEASE_VALIDATION_1.3.md"
$validationTarget = Join-Path $archive "04_分析与验证\当前版本验收.md"
Copy-Item -LiteralPath $validationSource -Destination $validationTarget -Force

Write-Host "Updated project archive: $archive"
Write-Host "Snapshot: $snapshotPath"
