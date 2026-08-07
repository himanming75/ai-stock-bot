[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m unittest tools.test_v14001_to_v15000_paper_autonomous_execution -v
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

python .\tools\run_v14001_to_v15000_paper_autonomous_execution.py --certify *> $null
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

Write-Host "VERIFY: PASS"
Write-Host "PAPER EXECUTION INTEGRATION: READY"
Write-Host "LIVE SUBMISSION: OFF"
