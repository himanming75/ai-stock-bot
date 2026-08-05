param([string]$Symbols="SPY,QQQ,IWM")
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python .\tools\run_actual_market_validation_read_only.py --symbols $Symbols
