$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python `
    .\tools\run_v641_to_v690_paper_order_ticket_builder.py
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
