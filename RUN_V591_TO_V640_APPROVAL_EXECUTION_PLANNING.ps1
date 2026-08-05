$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python `
    .\tools\run_v591_to_v640_approval_execution_planning.py
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
