$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_signal_risk_bridge_v78_41_to_v78_45 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_41_to_v78_45_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_41_to_v78_45_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.41-V78.45 PASS - READY TO COMMIT"
