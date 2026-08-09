$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Repo = "C:\stock-bot"
$LockPath = "$Repo\runtime\paper_autonomous_daily_session\session.lock"
$OutDir = "$Repo\runtime\regime_aware_buy_shadow_v2_9_3"
$BackupDir = "$OutDir\lock_backup"
$ReportPath = "$OutDir\latest_stale_lock_recovery_v2_9_3.json"

New-Item -ItemType Directory -Force $OutDir | Out-Null
New-Item -ItemType Directory -Force $BackupDir | Out-Null

Write-Host "=== V2.9.3 STALE SESSION LOCK SAFE RECOVERY ==="

$Report = [ordered]@{
    stage = "V2.9.3_STALE_SESSION_LOCK_SAFE_RECOVERY"
    status = $null
    generated_at_utc = [DateTime]::UtcNow.ToString("o")
    lock_path = $LockPath
    lock_existed_before = (Test-Path -LiteralPath $LockPath)
    lock_pid = $null
    lock_created_at_utc = $null
    pid_alive = $false
    stale_confirmed = $false
    backup_created = $false
    backup_path = $null
    lock_removed = $false
    lock_exists_after = $null
    contracts = [ordered]@{
        only_stale_lock_may_be_removed = $true
        live_process_lock_removal_forbidden = $true
        scheduled_task_modified = $false
        scheduled_task_started = $false
        paper_runtime_started = $false
        stop_file_removed = $false
        broker_write_performed = $false
        paper_order_submission_performed = $false
        live_order_submission_performed = $false
        production_parameter_modified = $false
        production_selector_modified = $false
        automatic_promotion = $false
    }
}

if(-not(Test-Path -LiteralPath $LockPath)){
    $Report.status = "PASS_NO_LOCK_PRESENT"
    $Report.lock_exists_after = $false
    $Report | ConvertTo-Json -Depth 12 | Set-Content -Path $ReportPath -Encoding UTF8
    $Report | ConvertTo-Json -Depth 12
    exit 0
}

try {
    $LockJson = Get-Content $LockPath -Raw | ConvertFrom-Json
} catch {
    $Report.status = "BLOCKED_LOCK_PARSE_ERROR"
    $Report.parse_error = $_.Exception.Message
    $Report.lock_exists_after = $true
    $Report | ConvertTo-Json -Depth 12 | Set-Content -Path $ReportPath -Encoding UTF8
    $Report | ConvertTo-Json -Depth 12
    exit 2
}

$Report.lock_pid = $LockJson.pid
$Report.lock_created_at_utc = $LockJson.created_at_utc

if($null -eq $LockJson.pid){
    $Report.status = "BLOCKED_LOCK_PID_MISSING"
    $Report.lock_exists_after = $true
    $Report | ConvertTo-Json -Depth 12 | Set-Content -Path $ReportPath -Encoding UTF8
    $Report | ConvertTo-Json -Depth 12
    exit 3
}

$PidValue = [int]$LockJson.pid
$Proc = Get-Process -Id $PidValue -ErrorAction SilentlyContinue

if($null -ne $Proc){
    $Report.pid_alive = $true
    $Report.status = "BLOCKED_LOCK_PROCESS_IS_ALIVE"
    $Report.lock_exists_after = $true
    $Report | ConvertTo-Json -Depth 12 | Set-Content -Path $ReportPath -Encoding UTF8
    $Report | ConvertTo-Json -Depth 12
    exit 4
}

$Report.stale_confirmed = $true

$Stamp = [DateTime]::UtcNow.ToString("yyyyMMdd_HHmmss")
$BackupPath = Join-Path $BackupDir "session.lock.$Stamp.bak"
Copy-Item -LiteralPath $LockPath -Destination $BackupPath -Force

if(-not(Test-Path -LiteralPath $BackupPath)){
    $Report.status = "BLOCKED_BACKUP_FAILED"
    $Report.lock_exists_after = $true
    $Report | ConvertTo-Json -Depth 12 | Set-Content -Path $ReportPath -Encoding UTF8
    $Report | ConvertTo-Json -Depth 12
    exit 5
}

$Report.backup_created = $true
$Report.backup_path = $BackupPath

Remove-Item -LiteralPath $LockPath -Force

if(Test-Path -LiteralPath $LockPath){
    $Report.status = "BLOCKED_LOCK_REMOVE_FAILED"
    $Report.lock_exists_after = $true
    $Report | ConvertTo-Json -Depth 12 | Set-Content -Path $ReportPath -Encoding UTF8
    $Report | ConvertTo-Json -Depth 12
    exit 6
}

$Report.lock_removed = $true
$Report.lock_exists_after = $false
$Report.status = "PASS_STALE_LOCK_BACKED_UP_AND_REMOVED"

$Report | ConvertTo-Json -Depth 12 | Set-Content -Path $ReportPath -Encoding UTF8
$Report | ConvertTo-Json -Depth 12
exit 0
