$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
Write-Host "V2.2.8 FAST HISTORICAL DATA ACCELERATION"
Write-Host "30 symbols | 1Min | IEX | ~90 calendar days"
Write-Host "Creates 5/15/30/60m forward labels + MFE/MAE + ML features"
Write-Host "Market-data network only. No broker trading endpoint. No orders."
. .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper
$env:PYTHONPATH=$Repo
& "$Repo\.venv\Scripts\python.exe" -m ai_engine_v2.fast_data_acceleration_cli_v2_2_8 `
 --root $Repo --mode backfill --lookback-days 90
if($LASTEXITCODE -ne 0){throw "V2.2.8 FAST BACKFILL FAILED"}
