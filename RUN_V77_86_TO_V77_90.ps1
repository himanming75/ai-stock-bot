$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_risk_stress_v77_86_to_v77_90 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v77_86_to_v77_90_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v77_86_to_v77_90_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V77.86-V77.90 PASS - READY TO COMMIT"
