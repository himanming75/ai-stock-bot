param(
    [switch]$AllowDuringMarket
)

[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

$Python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)){ throw "VENV PYTHON NOT FOUND: $Python" }

$env:LIVE_TRADING_ENABLED="false"
$env:ETRADE_LIVE_WRITE_ENABLED="false"
$env:ETRADE_LIVE_SUBMISSION_ENABLED="false"
$env:BROKER_WRITE_ENABLED="false"

$argsList=@(
  ".\tools\run_closed_trade_eod_v51_v55.py",
  "--repository-root",
  $PSScriptRoot
)

if($AllowDuringMarket){
  $argsList += "--allow-during-market"
}

& $Python @argsList
exit $LASTEXITCODE
