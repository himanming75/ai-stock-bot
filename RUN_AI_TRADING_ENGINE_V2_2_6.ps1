$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
& "$Repo\.venv\Scripts\python.exe" -m ai_engine_v2.champion_challenger_outcome_comparator_cli_v2_2_6 --root $Repo
if($LASTEXITCODE -ne 0){throw "V2.2.6 RUN FAILED"}
