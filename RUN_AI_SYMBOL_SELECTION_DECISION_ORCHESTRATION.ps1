param(
    [string]$MarketPath = "release/market_intelligence_data_fusion/actual/market_intelligence_snapshot.json",
    [string]$PolicyPath = "release/ai_symbol_selection_decision_orchestration/config/decision_policy.json",
    [string]$OutputPath = "release/ai_symbol_selection_decision_orchestration/actual/ai_decision_snapshot.json"
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python .\tools\run_ai_symbol_selection_decision_orchestration.py `
    --market $MarketPath --policy $PolicyPath --output $OutputPath
