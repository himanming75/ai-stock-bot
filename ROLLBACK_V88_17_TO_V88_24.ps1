param(
    [string]$ProjectPath = "C:\stock-bot",
    [string]$BackupRoot = "C:\stock-bot-backups",
    [string]$BackupPath = ""
)

$ErrorActionPreference = "Stop"

if (-not $BackupPath) {
    $Pointer = Join-Path $BackupRoot "LATEST_V88_17_TO_V88_24_BACKUP.txt"
    if (-not (Test-Path $Pointer)) {
        throw "Backup pointer not found: $Pointer"
    }
    $BackupPath = (Get-Content $Pointer -Raw).Trim()
}

if (-not (Test-Path $BackupPath)) {
    throw "Backup folder not found: $BackupPath"
}

Copy-Item `
    -Path (Join-Path $BackupPath "*") `
    -Destination $ProjectPath `
    -Recurse `
    -Force

Write-Host "ROLLBACK_COMPLETE_FROM=$BackupPath"
