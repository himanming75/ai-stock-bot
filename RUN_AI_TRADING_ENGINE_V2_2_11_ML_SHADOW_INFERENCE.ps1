$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo

$Python="$Repo\.venv_ml\Scripts\python.exe"
if(-not (Test-Path $Python)){
    throw "ML ENV MISSING. V2.2.10 .venv_ml is required."
}

Write-Host "V2.2.11 ML SHADOW INFERENCE"
Write-Host "Uses V2.2.8.1 feature engineering + V2.2.10 selected models"
Write-Host "Shadow only. Selector unchanged. Broker orders: NONE."

& $Python -m ai_engine_v2.ml_shadow_inference_cli_v2_2_11 --root $Repo --mode run
if($LASTEXITCODE -ne 0){throw "V2.2.11 SHADOW INFERENCE FAILED"}
