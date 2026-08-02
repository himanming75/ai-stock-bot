$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_op3_13_to_op3_16.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_limited_autonomous_paper_trading_op3_13_to_op3_16 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_OP3_13_TO_OP3_16_LIMITED_AUTONOMOUS_PAPER.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_limited_autonomous_paper_trading_op3_13_to_op3_16.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "OP3.13-OP3.16 TEST AND VERIFY PASS"
