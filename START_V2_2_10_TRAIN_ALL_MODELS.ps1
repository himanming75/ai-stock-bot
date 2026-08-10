$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$MlPython="$Repo\.venv_ml\Scripts\python.exe"

if(-not (Test-Path $MlPython)){
    throw "ML ENV MISSING. Run .\START_V2_2_10_SETUP_ML_ENV.ps1 first."
}

$env:PYTHONPATH=$Repo

Write-Host "V2.2.10 ML TRAINING"
Write-Host "Horizons: 5m / 15m / 30m / 60m"
Write-Host "Candidates: Dummy / Logistic / HistGradientBoosting"
Write-Host "Selection: VALIDATION ONLY"
Write-Host "TEST: evaluated only after winner is frozen"
Write-Host "Broker network: OFF | Orders: 0 | Live trading: LOCKED"

& $MlPython -m ai_engine_v2.ml_model_training_validation_cli_v2_2_10 `
 --root $Repo --mode train
if($LASTEXITCODE -ne 0){throw "V2.2.10 MODEL TRAINING FAILED"}
