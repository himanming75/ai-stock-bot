$ErrorActionPreference = "Stop"
python -m unittest tools.test_paper_execution_v77_51_to_v77_55 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\run_v77_51_to_v77_55_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\verify_v77_51_to_v77_55_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V77.51-V77.55 PASS - READY TO COMMIT"
