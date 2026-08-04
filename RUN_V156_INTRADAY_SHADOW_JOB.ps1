$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v156_operations_job.py intraday_shadow
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
