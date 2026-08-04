$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$typed = Read-Host "FINAL CONFIRMATION - type SUBMIT_ONE_DOLLAR_PAPER_ORDER"
if($typed -ne "SUBMIT_ONE_DOLLAR_PAPER_ORDER"){
  throw "Final confirmation phrase did not match."
}
python tools\run_v306_01_to_v310_64.py `
  --allow-paper-network `
  --submit-one-micro-order
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
