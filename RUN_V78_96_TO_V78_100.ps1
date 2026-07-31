$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_release_acceptance_v78_96_to_v78_100 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_96_to_v78_100_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_96_to_v78_100_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.96-V78.100 PASS - READY TO COMMIT"
