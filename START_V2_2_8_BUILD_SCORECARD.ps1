$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
& "$Repo\.venv\Scripts\python.exe" -m ai_engine_v2.continuous_shadow_learning_pipeline_cli_v2_2_8 --root $Repo --mode scorecard
if($LASTEXITCODE -ne 0){throw "V2.2.8 SCORECARD FAILED"}
Get-Content "$Repo\runtime\ai_continuous_shadow_learning_pipeline_v2_2_8\latest_performance_scorecard.json"
