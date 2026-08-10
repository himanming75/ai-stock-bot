$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
& "$Repo\.venv\Scripts\python.exe" -m ai_engine_v2.ml_model_training_validation_cli_v2_2_10 --root $Repo --mode preflight
if($LASTEXITCODE -ne 0){throw "V2.2.10 PREFLIGHT FAILED"}
