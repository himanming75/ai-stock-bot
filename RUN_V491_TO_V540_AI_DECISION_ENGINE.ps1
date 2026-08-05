$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python .\tools\run_v491_to_v540_ai_decision_engine.py
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
