$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

$PortfolioSnapshot = `
    ".\release\v321_330_realtime_portfolio_monitoring\actual\portfolio_monitor_latest.json"

$PortfolioMetricsLedger = `
    ".\release\v321_330_realtime_portfolio_monitoring\actual\portfolio_metrics_ledger.jsonl"

if(-not(Test-Path -LiteralPath $PortfolioSnapshot)){
    throw "V321-V330 portfolio snapshot is missing."
}

if(-not(Test-Path -LiteralPath $PortfolioMetricsLedger)){
    throw "V321-V330 portfolio metrics ledger is missing."
}

python `
    .\tools\run_v331_to_v340_realtime_risk_monitoring.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
