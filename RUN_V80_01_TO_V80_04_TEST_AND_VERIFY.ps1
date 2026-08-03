$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
python tools/install_check_v80_01_to_v80_04.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_paper_trading_completion_v80_01_to_v80_04 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V80_01_TO_V80_04_COMPLETION.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_paper_trading_completion_v80_01_to_v80_04.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host 'V80.01-V80.04 TEST AND VERIFY PASS'
