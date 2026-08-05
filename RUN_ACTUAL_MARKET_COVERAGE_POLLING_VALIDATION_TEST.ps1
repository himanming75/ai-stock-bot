$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_actual_market_coverage_polling_validation -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
