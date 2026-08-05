$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_ai_symbol_selection_decision_orchestration -v
python .\tools\verify_ai_symbol_selection_decision_orchestration.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
