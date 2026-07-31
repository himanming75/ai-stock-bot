$ErrorActionPreference = "Stop"
python -m unittest tools.test_paper_runtime_v77_16_to_v77_20 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\run_v77_16_to_v77_20_pipeline.py --repository-root . --clean --cycles 1000
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\verify_v77_16_to_v77_20_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V77.16-V77.20 PASS - READY TO COMMIT"
