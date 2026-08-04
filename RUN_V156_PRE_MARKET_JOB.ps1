$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v156_operations_job.py pre_market
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
