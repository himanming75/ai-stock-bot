$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
Write-Host "V2.2.8 LIVE 30-SYMBOL AI SHADOW COLLECTOR"
Write-Host "IEX latest minute bars | 60-second polling | max 8 hours"
Write-Host "AAPL/MSFT/SPY remain the existing Paper trading universe."
Write-Host "All extra symbols are AI data only. No order submission."
$Confirm=Read-Host "Type RUN_FAST_30_SYMBOL_SHADOW_COLLECTOR"
if($Confirm -ne "RUN_FAST_30_SYMBOL_SHADOW_COLLECTOR"){throw "CONFIRMATION MISMATCH"}
. .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper
$env:PYTHONPATH=$Repo
& "$Repo\.venv\Scripts\python.exe" -m ai_engine_v2.fast_data_acceleration_cli_v2_2_8 `
 --root $Repo --mode live --poll-seconds 60 --max-runtime-seconds 28800
if($LASTEXITCODE -ne 0){throw "V2.2.8 LIVE SHADOW COLLECTOR FAILED"}
