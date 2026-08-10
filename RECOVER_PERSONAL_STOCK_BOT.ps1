$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
$Port=8770
$HostAddr="127.0.0.1"
$Runtime="$Repo\runtime\personal_operations_launcher"
$StartScript="$Repo\START_PERSONAL_STOCK_BOT.ps1"

Set-Location $Repo
New-Item -ItemType Directory -Force $Runtime | Out-Null

Write-Host "=== PERSONAL AI STOCK BOT RECOVERY ==="

$Recovery=[ordered]@{
    started_at=(Get-Date).ToString("o")
    port=$Port
    actions=@()
    warnings=@()
}

$RunLock="$Repo\runtime\validation_auto_scheduler\RUN.lock"
if(Test-Path $RunLock){
    try{
        $Lock=Get-Content $RunLock -Raw | ConvertFrom-Json
        $LockPid=[int]$Lock.pid
        $Alive=$false
        if($LockPid -gt 0){
            $Alive=Get-Process -Id $LockPid -ErrorAction SilentlyContinue
        }
        if(-not $Alive){
            Remove-Item $RunLock -Force
            $Recovery.actions += "REMOVED_STALE_VALIDATION_RUN_LOCK"
            Write-Host "Removed stale Validation RUN.lock"
        }else{
            $Recovery.warnings += "VALIDATION_RUN_ACTIVE_PID_$LockPid"
            Write-Host "Validation run lock belongs to active PID $LockPid; preserved."
        }
    }catch{
        $Recovery.warnings += "RUN_LOCK_PARSE_FAILED"
    }
}

$Listener=Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1

if(-not $Listener){
    $Recovery.actions += "CONTROL_CENTER_RESTART"
    Write-Host "Control Center not running. Starting..."
    powershell -NoProfile -ExecutionPolicy Bypass -File $StartScript
    if($LASTEXITCODE -ne 0){ throw "RECOVERY_START_FAILED" }
}else{
    Write-Host "Control Center listener exists. PID: $($Listener.OwningProcess)"
}

try{
    $Daily=Invoke-RestMethod -Uri "http://$HostAddr`:$Port/api/daily-ops" -TimeoutSec 5
    $Recovery.actions += "DAILY_OPS_API_CONFIRMED"
    Write-Host "Daily Ops API: OK"
}catch{
    throw "DAILY_OPS_API_UNAVAILABLE_AFTER_RECOVERY"
}

# Verify scheduler is actually alive after startup.
if(-not $Daily.scheduler.running){
    $Body=@{ action="start_validation_scheduler" } | ConvertTo-Json
    $null=Invoke-RestMethod `
        -Uri "http://$HostAddr`:$Port/api/daily-ops/action" `
        -Method POST `
        -ContentType "application/json" `
        -Body $Body `
        -TimeoutSec 15

    $Deadline=(Get-Date).AddSeconds(8)
    do{
        Start-Sleep -Milliseconds 500
        $Daily=Invoke-RestMethod -Uri "http://$HostAddr`:$Port/api/daily-ops" -TimeoutSec 5
        if($Daily.scheduler.running){ break }
    }while((Get-Date) -lt $Deadline)

    if(-not $Daily.scheduler.running){
        throw "RECOVERY_VALIDATION_SCHEDULER_DID_NOT_STAY_RUNNING"
    }

    $Recovery.actions += "VALIDATION_SCHEDULER_STARTED"
    Write-Host "Validation Scheduler: STARTED PID $($Daily.scheduler.pid)"
}else{
    # Recheck after a short delay to avoid accepting a dying scheduler process.
    Start-Sleep -Seconds 2
    $Daily=Invoke-RestMethod -Uri "http://$HostAddr`:$Port/api/daily-ops" -TimeoutSec 5
    if(-not $Daily.scheduler.running){
        throw "RECOVERY_SCHEDULER_DIED_AFTER_INITIAL_CHECK"
    }
    Write-Host "Validation Scheduler: RUNNING PID $($Daily.scheduler.pid)"
}

$Body=@{ action="save_operations_snapshot" } | ConvertTo-Json
try{
    $Snap=Invoke-RestMethod `
        -Uri "http://$HostAddr`:$Port/api/daily-ops/action" `
        -Method POST `
        -ContentType "application/json" `
        -Body $Body `
        -TimeoutSec 15
    if($Snap.ok){
        $Recovery.actions += "RECOVERY_SNAPSHOT_SAVED"
        Write-Host "Recovery Operations Snapshot: SAVED"
    }
}catch{
    $Recovery.warnings += "RECOVERY_SNAPSHOT_FAILED"
}

$Recovery["finished_at"]=(Get-Date).ToString("o")
$Recovery["etrade"]="DEFERRED"
$Recovery["paper_orders_submitted_by_recovery"]=0
$Recovery["live_orders_submitted_by_recovery"]=0
$Recovery | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 (Join-Path $Runtime "latest_recovery.json")

Write-Host ""
Write-Host "RECOVERY: PASS"
Write-Host "Open: http://$HostAddr`:$Port"
