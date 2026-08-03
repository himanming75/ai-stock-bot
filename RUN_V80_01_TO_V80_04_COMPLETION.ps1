$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
Write-Host '=== V80.01-V80.04 PAPER TRADING COMPLETION PACKAGE ==='
Write-Host 'Local aggregation and integrity only. No broker or order operations.'
python tools/run_paper_trading_completion_v80_01_to_v80_04.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host 'V80.01-V80.04 COMPLETE'
