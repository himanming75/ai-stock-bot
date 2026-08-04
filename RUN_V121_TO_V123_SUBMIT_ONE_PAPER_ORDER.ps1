$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "WARNING: This submits ONE order to the Alpaca PAPER account."
$answer=Read-Host "Type PAPER to continue"
if($answer-ne "PAPER"){throw "CANCELLED"}
python tools\run_v121_01_to_v123_64.py --real-network --submit-paper-order
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
