param([string]$TargetPath="C:\stock-bot")
$ErrorActionPreference="Stop"
Set-Location $TargetPath

$Python=Join-Path $TargetPath ".venv\Scripts\python.exe"
$TaskName="AIStockBot-PaperValidationFinalizeStart"

$env:APCA_API_KEY_ID=[Environment]::GetEnvironmentVariable("APCA_API_KEY_ID","User")
$env:APCA_API_SECRET_KEY=[Environment]::GetEnvironmentVariable("APCA_API_SECRET_KEY","User")
$env:LIVE_TRADING_ENABLED="false"
$env:ETRADE_LIVE_WRITE_ENABLED="false"
$env:ETRADE_LIVE_SUBMISSION_ENABLED="false"
$env:BROKER_WRITE_ENABLED="false"

Write-Host "=== PAPER VALIDATION FINALIZER V1.2 ==="

# Hard safety: regular paper task must still be disabled until flat.
$PaperTask=Get-ScheduledTask -TaskName "AIStockBot-PaperAutonomousDailySession" -ErrorAction SilentlyContinue
if($PaperTask -and $PaperTask.State -ne "Disabled"){
    Disable-ScheduledTask -TaskName "AIStockBot-PaperAutonomousDailySession"|Out-Null
}

Write-Host "[1/7] CHECK / COMPLETE OLD PAPER FLATTEN"
& $Python ".\tools\paper_flatten_idempotent.py" "$TargetPath"
$FlatCode=$LASTEXITCODE

if($FlatCode -eq 10){
    Write-Host "MARKET CLOSED - EXISTING CLOSE ORDERS LEFT UNCHANGED"
    Write-Host "FINALIZER WILL RETRY AT NEXT SCHEDULED RUN"
    exit 0
}
if($FlatCode -ne 0){
    throw "PAPER ACCOUNT FLATTEN FAILED OR TIMED OUT"
}
Write-Host "PAPER ACCOUNT FLAT: PASS"

Write-Host "[2/7] VERIFY DAY-1 PLAN = 15"
$Plan=Get-Content ".\config\paper_validation_2week_300.json" -Raw|ConvertFrom-Json
$Day1=$Plan.daily_entry_caps|Where-Object{$_.day -eq 1}|Select-Object -First 1
if(-not $Day1 -or [int]$Day1.maximum_daily_entries -ne 15){
    throw "DAY1 PLAN CONTRACT FAILED"
}
if([int]$Plan.target_closed_trades -ne 300){
    throw "300 CLOSED-TRADE TARGET CONTRACT FAILED"
}
Write-Host "DAY1 CAP: 15"
Write-Host "TARGET: 300 CLOSED TRADES"

Write-Host "[3/7] RESET BASELINE AFTER OLD POSITIONS ARE FLAT"
$Runtime=Join-Path $TargetPath "runtime\paper_validation_2week_300"
New-Item -ItemType Directory -Path $Runtime -Force|Out-Null
$ClosedPath=Join-Path $TargetPath "runtime\paper_full_auto_lifecycle\closed_round_trips.jsonl"
$ClosedCount=0
if(Test-Path $ClosedPath){
    $ClosedCount=@(Get-Content $ClosedPath|Where-Object{$_.Trim()}).Count
}
$Baseline=[ordered]@{
    validation_id=$Plan.validation_id
    created_at_utc=(Get-Date).ToUniversalTime().ToString("o")
    baseline_closed_trade_count=$ClosedCount
    target_closed_trades=300
    start_date=$Plan.start_date
    end_date=$Plan.end_date
    paper_account_flat_at_start=$true
}
$Baseline|ConvertTo-Json|Set-Content (Join-Path $Runtime "baseline.json") -Encoding UTF8
$Baseline|ConvertTo-Json

Write-Host "[4/7] FINAL REGRESSION"
& $Python -m unittest tools.test_v14001_to_v15000_paper_autonomous_execution -v
if($LASTEXITCODE-ne 0){throw "V14001 TEST FAILED"}
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\RUN_DAILY_SESSION_SHADOW_GUARD_INTEGRATION_TEST.ps1
if($LASTEXITCODE-ne 0){throw "SHADOW TEST FAILED"}
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\RUN_PAPER_AUTONOMOUS_DAILY_SESSION_TEST.ps1
if($LASTEXITCODE-ne 0){throw "DAILY SESSION TEST FAILED"}
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\RUN_V14001_TO_V15000_TEST.ps1
if($LASTEXITCODE-ne 0){throw "CERTIFICATION TEST FAILED"}
Write-Host "FINAL REGRESSION: PASS"

Write-Host "[5/7] ARM ALPACA PAPER ONLY"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ARM_PAPER_ONLY_V14001_TO_V15000.ps1
if($LASTEXITCODE-ne 0){throw "PAPER ARM FAILED"}
Write-Host "PAPER ARM: PASS"

Write-Host "[6/7] COMMIT / PUSH VALIDATION SOURCE"
$Paths=@(
    "RUN_PAPER_AUTONOMOUS_DAILY_SESSION.ps1",
    "paper_daily_session/shadow_integration.py",
    "paper_daily_session/runner.py",
    "paper_autonomous_execution/signals.py",
    "paper_autonomous_execution/alpaca_paper.py",
    "paper_autonomous_execution/service.py",
    "tools/test_daily_session_shadow_guard_integration.py",
    "config/paper_validation_2week_300.json",
    "config/smart_safe_guard_policy.json",
    "tools/paper_flatten_idempotent.py",
    "RUN_FINALIZE_PAPER_VALIDATION_START.ps1"
)
git add -- $Paths
if($LASTEXITCODE-ne 0){throw "GIT ADD FAILED"}
$Staged=@(git diff --cached --name-only)
if($Staged.Count -gt 0){
    git commit -m "Finalize two-week 300-trade paper validation startup"
    if($LASTEXITCODE-ne 0){throw "LOCAL COMMIT FAILED"}
}
git push origin main
if($LASTEXITCODE-ne 0){throw "GITHUB PUSH FAILED"}
Write-Host "GITHUB PUSH: PASS"

Write-Host "[7/7] ENABLE PAPER AUTO-TRADING"
Disable-ScheduledTask -TaskName "AIStockBot-PaperRoundtripValidationGate" -ErrorAction SilentlyContinue|Out-Null
Enable-ScheduledTask -TaskName "AIStockBot-PaperAutonomousDailySession"|Out-Null

# The daily trigger can pass before flattening finishes. Start immediately after flat confirmation.
Start-ScheduledTask -TaskName "AIStockBot-PaperAutonomousDailySession"
Start-Sleep -Seconds 2
Write-Host "PAPER AUTO-TRADING IMMEDIATE START: REQUESTED"

# Disable this finalizer so it does not run again after successful startup.
Disable-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue|Out-Null

$PaperTask=Get-ScheduledTask -TaskName "AIStockBot-PaperAutonomousDailySession"
$PaperInfo=Get-ScheduledTaskInfo -TaskName "AIStockBot-PaperAutonomousDailySession"

Write-Host ""
Write-Host "===================================================="
Write-Host "2-WEEK / 300 PAPER VALIDATION: ACTIVE"
Write-Host "DAY 1 MAX NEW ENTRIES: 15"
Write-Host "TARGET: 300 CLOSED ROUND TRIPS"
Write-Host "STARTING POSITIONS: 0"
Write-Host "PAPER AUTO-TRADING TASK: $($PaperTask.State)"
Write-Host "NEXT RUN: $($PaperInfo.NextRunTime)"
Write-Host "ETRADE LIVE WRITE: OFF"
Write-Host "LIVE AUTO-ENABLE: NO"
Write-Host "===================================================="
