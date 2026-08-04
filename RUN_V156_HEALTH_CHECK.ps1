$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v156_operations_job.py health_check
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
