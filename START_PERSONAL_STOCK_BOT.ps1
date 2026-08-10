$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
$Port=8770
$HostAddr="127.0.0.1"
$Python="$Repo\.venv\Scripts\python.exe"
$Runner="$Repo\tools\run_v141_01_to_v145_64.py"
$Runtime="$Repo\runtime\personal_operations_launcher"

Set-Location $Repo
New-Item -ItemType Directory -Force $Runtime | Out-Null

function Get-Listener {
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
}
function Wait-HttpReady {
    param([int]$Seconds=20)
    $Deadline=(Get-Date).AddSeconds($Seconds)
    while((Get-Date) -lt $Deadline){
        try{
            $r=Invoke-RestMethod -Uri "http://$HostAddr`:$Port/api/daily-ops" -TimeoutSec 2
            if($r.system.control_center -eq "RUNNING"){ return $true }
        }catch{}
        Start-Sleep -Milliseconds 500
    }
    return $false
}
function Get-DailyOps {
    Invoke-RestMethod -Uri "http://$HostAddr`:$Port/api/daily-ops" -TimeoutSec 5
}
function Ensure-ValidationScheduler {
    $Daily=Get-DailyOps
    if($Daily.scheduler.running){
        return $Daily.scheduler
    }

    $Body=@{ action="start_validation_scheduler" } | ConvertTo-Json
    $null=Invoke-RestMethod `
        -Uri "http://$HostAddr`:$Port/api/daily-ops/action" `
        -Method POST `
        -ContentType "application/json" `
        -Body $Body `
        -TimeoutSec 15

    # Verify actual survival, not only the immediate start response.
    $Deadline=(Get-Date).AddSeconds(8)
    do{
        Start-Sleep -Milliseconds 500
        $Daily=Get-DailyOps
        if($Daily.scheduler.running){
            return $Daily.scheduler
        }
    }while((Get-Date) -lt $Deadline)

    throw "VALIDATION_SCHEDULER_DID_NOT_STAY_RUNNING"
}

Write-Host "=== PERSONAL AI STOCK BOT START ==="

if(-not (Test-Path $Python)){ throw "PYTHON_NOT_FOUND: $Python" }
if(-not (Test-Path $Runner)){ throw "WEB_RUNNER_NOT_FOUND: $Runner" }

$Listener=Get-Listener
if($Listener){
    Write-Host "Control Center already listening on port $Port. PID: $($Listener.OwningProcess)"
}else{
    $OutLog=Join-Path $Runtime "control_center_8770_stdout.log"
    $ErrLog=Join-Path $Runtime "control_center_8770_stderr.log"
    $Args=@("-B",$Runner,"--host",$HostAddr,"--port","$Port")

    $Proc=Start-Process `
        -FilePath $Python `
        -ArgumentList $Args `
        -WorkingDirectory $Repo `
        -RedirectStandardOutput $OutLog `
        -RedirectStandardError $ErrLog `
        -PassThru `
        -WindowStyle Hidden

    Write-Host "Starting Control Center launcher PID: $($Proc.Id)"

    if(-not (Wait-HttpReady -Seconds 20)){
        throw "CONTROL_CENTER_START_TIMEOUT"
    }

    $Listener=Get-Listener
    if($Listener){
        Write-Host "Control Center READY. Listener PID: $($Listener.OwningProcess)"
    }
}

$Scheduler=Ensure-ValidationScheduler
Write-Host "Validation Scheduler: READY PID $($Scheduler.pid)"

$Body=@{ action="save_operations_snapshot" } | ConvertTo-Json
try{
    $Snap=Invoke-RestMethod `
        -Uri "http://$HostAddr`:$Port/api/daily-ops/action" `
        -Method POST `
        -ContentType "application/json" `
        -Body $Body `
        -TimeoutSec 15
    if($Snap.ok){ Write-Host "Startup Operations Snapshot: SAVED" }
}catch{
    Write-Warning "Startup snapshot could not be saved."
}

$Listener=Get-Listener
$State=[ordered]@{
    started_at=(Get-Date).ToString("o")
    host=$HostAddr
    port=$Port
    control_center_pid=if($Listener){$Listener.OwningProcess}else{$null}
    validation_scheduler_pid=$Scheduler.pid
    url="http://$HostAddr`:$Port"
    etrade="DEFERRED"
    paper_orders_submitted_by_launcher=0
    live_orders_submitted_by_launcher=0
}
$State | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 (Join-Path $Runtime "launcher_state.json")

Write-Host ""
Write-Host "PERSONAL AI STOCK BOT: READY"
Write-Host "Open: http://$HostAddr`:$Port"
Write-Host "E*TRADE: DEFERRED"
Write-Host "Paper orders from launcher: 0"
Write-Host "Live orders from launcher: 0"
