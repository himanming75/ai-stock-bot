$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
& "$Repo\.venv\Scripts\python.exe" -m ai_engine_v2.ml_model_health_bundle_cli_v2_2_16_18
if($LASTEXITCODE -ne 0){throw "V2.2.16-18 MODEL HEALTH BUNDLE FAILED"}
