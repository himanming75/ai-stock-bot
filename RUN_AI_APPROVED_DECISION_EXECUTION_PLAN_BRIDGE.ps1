$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python .\tools\run_ai_approved_decision_execution_plan_bridge.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
