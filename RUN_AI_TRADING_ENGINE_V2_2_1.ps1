$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
& "$Repo\.venv\Scripts\python.exe" -m ai_engine_v2.signal_scoring_feature_snapshot_cli_v2_2_1 --root $Repo
if($LASTEXITCODE -ne 0){throw "V2.2.1 RUN FAILED"}
