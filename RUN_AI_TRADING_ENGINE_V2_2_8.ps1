$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
& "$Repo\.venv\Scripts\python.exe" -m ai_engine_v2.continuous_shadow_learning_pipeline_cli_v2_2_8 --root $Repo --mode once --force
if($LASTEXITCODE -ne 0){throw "V2.2.8 ONE-CYCLE RUN FAILED"}
