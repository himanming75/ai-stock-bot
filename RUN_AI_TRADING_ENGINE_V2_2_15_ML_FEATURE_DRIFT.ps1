$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"
& $Python -m ai_engine_v2.ml_feature_drift_cli_v2_2_15 --root $Repo --mode evaluate
if($LASTEXITCODE -ne 0){throw "V2.2.15 FEATURE DRIFT EVALUATION FAILED"}
