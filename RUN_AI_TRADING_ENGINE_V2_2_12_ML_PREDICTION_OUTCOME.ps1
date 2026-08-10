$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

Write-Host "V2.2.12 ML PREDICTION OUTCOME RESOLVER"
Write-Host "Resolves V2.2.11 predictions against later V2.2.8.1 real market bars"
Write-Host "Research only. Selector unchanged. Broker orders: NONE."

& $Python -m ai_engine_v2.ml_prediction_outcome_cli_v2_2_12 --root $Repo --mode resolve
if($LASTEXITCODE -ne 0){throw "V2.2.12 OUTCOME RESOLUTION FAILED"}
