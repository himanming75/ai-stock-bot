$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_actual_market_validation_read_only -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
