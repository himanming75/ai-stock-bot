$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$Port=8886

Write-Host "=== V3.16 DIRECT SERVER VERIFY ==="

$Old=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
foreach($L in $Old){Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue}

$P=Start-Process -FilePath $Python -ArgumentList @(
 "C:\stock-bot\dashboard\operations_dashboard_v3_2.py",
 "--root","C:\stock-bot","--host","127.0.0.1","--port","$Port"
) -WorkingDirectory "C:\stock-bot" -PassThru

try{
 Start-Sleep -Seconds 5
 $S=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status" -TimeoutSec 20
 $R=$S.trade_analytics.market_regime_analysis

 Write-Host "VISUALIZATION STATUS:" $S.visualization_status
 Write-Host "TRADE ANALYTICS STATUS:" $S.trade_analytics_status
 Write-Host "REGIME STATUS:" $R.status
 Write-Host "SAMPLE STATUS:" $R.sample_status
 Write-Host "CANONICAL TRADE COUNT:" $R.canonical_trade_count
 Write-Host "CANONICAL NUMERIC TRADE COUNT:" $R.canonical_numeric_trade_count
 Write-Host "EVIDENCE TRADE COUNT:" $R.evidence_trade_count
 Write-Host "DIRECTION COVERAGE:" $R.coverage.direction_coverage
 Write-Host "VOLATILITY COVERAGE:" $R.coverage.volatility_coverage
 Write-Host "EVIDENCE SOURCE COUNT:" @($R.evidence_source_files).Count

 foreach($Row in @($R.direction_regimes)){
   Write-Host "DIRECTION:" $Row.name $Row.sample_status $Row.numeric_trade_count $Row.net_realized_pnl
 }
 foreach($Row in @($R.volatility_regimes)){
   Write-Host "VOLATILITY:" $Row.name $Row.sample_status $Row.numeric_trade_count $Row.net_realized_pnl
 }

 if($S.visualization_status -ne "PASS"){throw "VISUALIZATION REGRESSION"}
 if($S.trade_analytics_status -ne "PASS"){throw "TRADE ANALYTICS NOT PASS"}
 if($R.canonical_numeric_trade_count -ne $S.trade_analytics.historical.numeric_trade_count){throw "REGIME TRADE COUNT MISMATCH"}
 if($R.canonical_numeric_trade_count -lt 10 -and $R.sample_status -ne "INSUFFICIENT_SAMPLE"){throw "REGIME SAMPLE GUARD FAILED"}
 if(-not $R.contracts.explicit_evidence_only){throw "EXPLICIT EVIDENCE CONTRACT FAILED"}
 if($R.contracts.price_based_regime_inference_used){throw "PRICE INFERENCE CONTRACT FAILED"}
 if($R.contracts.unobserved_regimes_fabricated){throw "UNOBSERVED FABRICATION CONTRACT FAILED"}
 if($R.contracts.broker_write_performed){throw "BROKER WRITE CONTRACT FAILED"}
 if($R.contracts.paper_runtime_modified){throw "PAPER RUNTIME CONTRACT FAILED"}
 if($R.contracts.live_approval){throw "LIVE APPROVAL CONTRACT FAILED"}

 Write-Host "=== UTF8 UI VERIFY ==="
 & $Python .\dashboard\verify_market_regime_utf8_v3_16.py --url "http://127.0.0.1:$Port/"
 if($LASTEXITCODE -ne 0){throw "V3.16 UTF8 UI VERIFY FAILED"}

 Write-Host "DIRECT SERVER VERIFY: PASS"
}
finally{
 Stop-Process -Id $P.Id -Force -ErrorAction SilentlyContinue
}

Write-Host "VERIFY: PASS"
