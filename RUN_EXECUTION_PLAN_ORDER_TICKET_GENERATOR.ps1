$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python .\tools\run_execution_plan_order_ticket_generator.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
