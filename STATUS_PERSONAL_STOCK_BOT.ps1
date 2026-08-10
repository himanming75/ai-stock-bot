$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
$Port=8770
$HostAddr="127.0.0.1"
Set-Location $Repo

Write-Host "=== PERSONAL AI STOCK BOT STATUS ==="

$Listener=Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1

if(-not $Listener){
    Write-Host "Control Center: STOPPED"
    exit 0
}

Write-Host "Control Center: RUNNING"
Write-Host "PID: $($Listener.OwningProcess)"

try{
    $r=Invoke-RestMethod -Uri "http://$HostAddr`:$Port/api/daily-ops" -TimeoutSec 5
    Write-Host "System:" $r.system.state
    Write-Host "Validation:" "$($r.validation.days_completed)/$($r.validation.days_target)"
    Write-Host "Resolved:" "$($r.validation.resolved_outcomes)/$($r.validation.resolved_target)"
    Write-Host "AI Health:" $r.validation.ai_health
    Write-Host "Final Decision:" $r.validation.final_decision
    Write-Host "Scheduler Running:" $r.scheduler.running
    Write-Host "Scheduler PID:" $r.scheduler.pid
    Write-Host "Today's Action:" $r.today_action.action
    Write-Host "Live Orders From Daily Ops:" $r.safety.live_orders_submitted_by_daily_ops
}catch{
    Write-Warning "Daily Ops API unavailable: $($_.Exception.Message)"
}
