$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_walk_forward_v77_76_to_v77_80 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v77_76_to_v77_80_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v77_76_to_v77_80_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V77.76-V77.80 PASS - READY TO COMMIT"
