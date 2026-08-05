param(
    [string]$InputPath = "release/market_intelligence_data_fusion/fixtures/sample_market_data.json",
    [string]$OutputPath = "release/market_intelligence_data_fusion/actual/market_intelligence_snapshot.json"
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python .\tools\run_market_intelligence_data_fusion.py --input $InputPath --output $OutputPath
