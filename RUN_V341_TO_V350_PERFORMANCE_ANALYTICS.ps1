$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

$Metrics = `
    ".\release\v321_330_realtime_portfolio_monitoring\actual\portfolio_metrics_ledger.jsonl"
$Portfolio = `
    ".\release\v321_330_realtime_portfolio_monitoring\actual\portfolio_monitor_latest.json"
$Risk = `
    ".\release\v331_340_realtime_risk_monitoring\actual\risk_monitor_latest.json"

foreach($Path in @($Metrics,$Portfolio,$Risk)){
    if(-not(Test-Path -LiteralPath $Path)){
        throw "Required analytics input missing: $Path"
    }
}

python `
    .\tools\run_v341_to_v350_performance_analytics.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
