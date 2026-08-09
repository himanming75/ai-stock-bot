$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"
$Port=8895

$Old=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
foreach($L in $Old){Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue}

$P=Start-Process `
 -FilePath $Python `
 -ArgumentList @(
  "C:\stock-bot\dashboard\operations_dashboard_v3_2.py",
  "--root","C:\stock-bot",
  "--host","127.0.0.1",
  "--port","$Port"
 ) `
 -WorkingDirectory "C:\stock-bot" `
 -PassThru

try{
 Start-Sleep -Seconds 6
 $S=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status" -TimeoutSec 30
 $V=$S.broker_integration_v1.v2_etrade_readonly_oauth.bounded_multi_cycle_v2_1_4

 Write-Host "V2.1.4 STATUS:" $V.status
 Write-Host "DEVELOPMENT:" $V.development_status
 Write-Host "MAX CYCLES:" $V.maximum_cycles
 Write-Host "DUPLICATE GUARD:" $V.duplicate_signal_guard
 Write-Host "KILL SWITCH:" $V.kill_switch_supported
 Write-Host "UNBOUNDED LOOP:" $V.unbounded_loop_allowed
 Write-Host "PROD POST:" $V.production_order_post_allowed
 Write-Host "LIVE:" $V.live_trading_enabled

 if($V.development_status -ne "COMPLETE"){throw "V2.1.4 DEVELOPMENT FAILED"}
 if($V.maximum_cycles -ne 3){throw "MAX CYCLES POLICY FAILED"}
 if(-not $V.duplicate_signal_guard){throw "DUPLICATE GUARD FAILED"}
 if(-not $V.kill_switch_supported){throw "KILL SWITCH FAILED"}
 if($V.unbounded_loop_allowed){throw "UNBOUNDED LOOP MUST BE BLOCKED"}
 if($V.production_order_post_allowed){throw "PROD ORDER POST UNLOCKED"}
 if($V.live_trading_enabled){throw "LIVE TRADING ENABLED"}
 if($V.contracts.duplicate_order_engine_created){throw "DUPLICATE ORDER ENGINE"}
 if($V.contracts.duplicate_ledger_created){throw "DUPLICATE LEDGER"}
 if($V.contracts.duplicate_reconciliation_engine_created){throw "DUPLICATE RECONCILIATION ENGINE"}

 & $Python .\dashboard\verify_etrade_sandbox_bounded_multi_cycle_v2_1_4_utf8.py --url "http://127.0.0.1:$Port/"
 if($LASTEXITCODE -ne 0){throw "V2.1.4 UTF8 VERIFY FAILED"}

 Write-Host "VERIFY: PASS"
}
finally{
 Stop-Process -Id $P.Id -Force -ErrorAction SilentlyContinue
}
