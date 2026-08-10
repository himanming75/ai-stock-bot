$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
& "$Repo\.venv\Scripts\python.exe" -m ai_engine_v2.outcome_labeling_feature_trade_binding_cli_v2_2_2 --root $Repo
if($LASTEXITCODE -ne 0){throw "V2.2.2 RUN FAILED"}
