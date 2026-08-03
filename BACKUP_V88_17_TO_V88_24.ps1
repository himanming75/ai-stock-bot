param(
    [string]$ProjectPath = "C:\stock-bot",
    [string]$BackupRoot = "C:\stock-bot-backups"
)

$ErrorActionPreference = "Stop"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupPath = Join-Path $BackupRoot "v88_17_to_v88_24_$Timestamp"

New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null

$Targets = @(
    "paper_production_release",
    "dashboard_v2\paper_production_release_integration.py",
    "tools\run_paper_production_release_v88_17_to_v88_24.py",
    "tools\test_paper_production_release_v88_17_to_v88_24.py",
    "tools\install_check_v88_17_to_v88_24.py",
    "tools\verify_paper_production_release_v88_17_to_v88_24.py",
    "release\v88_17_to_v88_24"
)

foreach ($Target in $Targets) {
    $Source = Join-Path $ProjectPath $Target
    if (Test-Path $Source) {
        $Destination = Join-Path $BackupPath $Target
        $Parent = Split-Path $Destination -Parent
        New-Item -ItemType Directory -Path $Parent -Force | Out-Null
        Copy-Item $Source $Destination -Recurse -Force
    }
}

Set-Content `
    -Path (Join-Path $BackupRoot "LATEST_V88_17_TO_V88_24_BACKUP.txt") `
    -Value $BackupPath `
    -Encoding UTF8

Write-Host "BACKUP_PATH=$BackupPath"
