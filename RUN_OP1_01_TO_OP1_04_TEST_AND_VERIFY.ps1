$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python tools/install_check_op1_01_to_op1_04.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m unittest tools.test_paper_operations_pilot_op1_01_to_op1_04 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
powershell -ExecutionPolicy Bypass -File .\RUN_OP1_01_TO_OP1_04_PAPER_OPERATIONS_PILOT.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_paper_operations_pilot_op1_01_to_op1_04.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "OP1.01-OP1.04 TEST AND VERIFY PASS"
