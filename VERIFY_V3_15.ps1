$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python="C:\stock-bot\.venv\Scripts\python.exe"
$Port=8885

Write-Host "=== V3.15 DIRECT SERVER VERIFY ==="

$Old=@(
 Get-NetTCPConnection `
  -LocalPort $Port `
  -State Listen `
  -ErrorAction SilentlyContinue
)
foreach($L in $Old){
 Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue
}

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
 Start-Sleep -Seconds 5

 $S=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status" -TimeoutSec 20
 $R=$S.trade_analytics.strategy_robustness
 $B=$R.failure_boundaries

 Write-Host "VISUALIZATION STATUS:" $S.visualization_status
 Write-Host "TRADE ANALYTICS STATUS:" $S.trade_analytics_status
 Write-Host "ROBUSTNESS STATUS:" $R.status
 Write-Host "SAMPLE STATUS:" $R.sample_status
 Write-Host "CANONICAL TRADE COUNT:" $R.canonical_numeric_trade_count
 Write-Host "ROBUSTNESS SCORE:" $R.robustness_score
 Write-Host "RAW ROBUSTNESS SCORE:" $R.raw_robustness_score

 Write-Host "FRICTION STATUS:" $B.break_even_friction_bps_per_leg.status
 Write-Host "FRICTION BOUNDARY:" $B.break_even_friction_bps_per_leg.boundary
 Write-Host "WINNER HAIRCUT STATUS:" $B.winner_haircut_pct.status
 Write-Host "WINNER HAIRCUT BOUNDARY:" $B.winner_haircut_pct.boundary
 Write-Host "LOSS AMPLIFICATION STATUS:" $B.loss_amplification_pct.status
 Write-Host "LOSS AMPLIFICATION BOUNDARY:" $B.loss_amplification_pct.boundary
 Write-Host "PF=1 STATUS:" $B.profit_factor_one_friction_bps_per_leg.status
 Write-Host "PF=1 BOUNDARY:" $B.profit_factor_one_friction_bps_per_leg.boundary_bps_per_leg
 Write-Host "READINESS BOUNDARY STATUS:" $B.readiness_failure_friction_bps_per_leg.status
 Write-Host "READINESS BOUNDARY:" $B.readiness_failure_friction_bps_per_leg.boundary_bps_per_leg

 if($S.visualization_status -ne "PASS"){throw "VISUALIZATION REGRESSION"}
 if($S.trade_analytics_status -ne "PASS"){throw "TRADE ANALYTICS NOT PASS"}
 if($R.canonical_numeric_trade_count -ne $S.trade_analytics.historical.numeric_trade_count){throw "ROBUSTNESS TRADE COUNT MISMATCH"}
 if($R.canonical_numeric_trade_count -lt 10 -and $R.sample_status -ne "INSUFFICIENT_SAMPLE"){throw "ROBUSTNESS SAMPLE GUARD FAILED"}
 if($R.canonical_numeric_trade_count -lt 10 -and [double]$R.robustness_score -gt 49){throw "ROBUSTNESS SCORE SAMPLE CAP FAILED"}
 if(-not $R.contracts.simulation_only){throw "SIMULATION CONTRACT FAILED"}
 if($R.contracts.canonical_runtime_files_modified){throw "CANONICAL RUNTIME MUTATION CONTRACT FAILED"}
 if($R.contracts.broker_write_performed){throw "BROKER WRITE CONTRACT FAILED"}
 if($R.contracts.paper_runtime_modified){throw "PAPER RUNTIME CONTRACT FAILED"}
 if($R.contracts.live_approval){throw "LIVE APPROVAL CONTRACT FAILED"}

 if(-not $R.observability.has_losses){
  if($B.loss_amplification_pct.status -ne "UNOBSERVED_NO_LOSING_TRADES"){
   throw "LOSS BOUNDARY OBSERVABILITY GUARD FAILED"
  }
 }

 Write-Host "=== UTF8 UI VERIFY ==="

 & $Python .\dashboard\verify_strategy_robustness_utf8_v3_15.py --url "http://127.0.0.1:$Port/"
 if($LASTEXITCODE -ne 0){throw "V3.15 UTF8 UI VERIFY FAILED"}

 Write-Host "DIRECT SERVER VERIFY: PASS"
}
finally{
 Stop-Process -Id $P.Id -Force -ErrorAction SilentlyContinue
}

Write-Host "VERIFY: PASS"
