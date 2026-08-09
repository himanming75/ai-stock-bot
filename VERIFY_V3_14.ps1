$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$Port=8884

Write-Host "=== V3.14 DIRECT SERVER VERIFY ==="

$Old=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
foreach($L in $Old){Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue}

$P=Start-Process -FilePath $Python -ArgumentList @(
 "C:\stock-bot\dashboard\operations_dashboard_v3_2.py",
 "--root","C:\stock-bot","--host","127.0.0.1","--port","$Port"
) -WorkingDirectory "C:\stock-bot" -PassThru

try{
 Start-Sleep -Seconds 5

 $S=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status" -TimeoutSec 20
 $ST=$S.trade_analytics.strategy_stress_test
 $Scenarios=@($ST.scenarios)

 Write-Host "VISUALIZATION STATUS:" $S.visualization_status
 Write-Host "TRADE ANALYTICS STATUS:" $S.trade_analytics_status
 Write-Host "STRESS STATUS:" $ST.status
 Write-Host "SAMPLE STATUS:" $ST.sample_status
 Write-Host "CANONICAL TRADE COUNT:" $ST.canonical_numeric_trade_count
 Write-Host "SCENARIO COUNT:" $ST.scenario_count
 Write-Host "SEVERE DEGRADATION:" $ST.severe_degradation_pct

 foreach($Scenario in $Scenarios){
   Write-Host "---" $Scenario.scenario.id "---"
   Write-Host "NET PNL:" $Scenario.stats.net_realized_pnl
   Write-Host "WIN RATE:" $Scenario.stats.win_rate
   Write-Host "PROFIT FACTOR:" $Scenario.stats.profit_factor
   Write-Host "MAX DRAWDOWN:" $Scenario.stats.max_realized_drawdown
   Write-Host "READINESS:" $Scenario.readiness.status
   Write-Host "READINESS SCORE:" $Scenario.readiness.overall_score
   Write-Host "FRICTION COST:" $Scenario.total_friction_cost
 }

 if($S.visualization_status -ne "PASS"){throw "VISUALIZATION REGRESSION"}
 if($S.trade_analytics_status -ne "PASS"){throw "TRADE ANALYTICS NOT PASS"}
 if($ST.scenario_count -ne 4){throw "STRESS SCENARIO COUNT INVALID"}
 if($ST.canonical_numeric_trade_count -ne $S.trade_analytics.historical.numeric_trade_count){throw "STRESS TRADE COUNT MISMATCH"}
 if($ST.canonical_numeric_trade_count -lt 10 -and $ST.sample_status -ne "INSUFFICIENT_SAMPLE"){throw "STRESS SAMPLE GUARD FAILED"}
 if(-not $ST.contracts.simulation_only){throw "SIMULATION CONTRACT FAILED"}
 if($ST.contracts.canonical_trades_modified){throw "CANONICAL MUTATION CONTRACT FAILED"}
 if($ST.contracts.broker_write_performed){throw "BROKER WRITE CONTRACT FAILED"}
 if($ST.contracts.paper_runtime_modified){throw "PAPER RUNTIME CONTRACT FAILED"}
 if($ST.contracts.live_approval){throw "LIVE APPROVAL CONTRACT FAILED"}

 if($Scenarios.Count -eq 4){
   $Base=[double]$Scenarios[0].stats.net_realized_pnl
   $Severe=[double]$Scenarios[3].stats.net_realized_pnl
   if($Severe -gt $Base){throw "SEVERE STRESS IMPROVED PNL UNEXPECTEDLY"}
 }

 Write-Host "=== UTF8 UI VERIFY ==="
 & $Python .\dashboard\verify_strategy_stress_test_utf8_v3_14.py --url "http://127.0.0.1:$Port/"
 if($LASTEXITCODE -ne 0){throw "V3.14 UTF8 UI VERIFY FAILED"}

 Write-Host "DIRECT SERVER VERIFY: PASS"
}
finally{
 Stop-Process -Id $P.Id -Force -ErrorAction SilentlyContinue
}

Write-Host "VERIFY: PASS"
