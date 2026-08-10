$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
& "$Repo\.venv\Scripts\python.exe" -m ai_engine_v2.threshold_calibration_challenger_policy_builder_cli_v2_2_4 --root $Repo
if($LASTEXITCODE -ne 0){throw "V2.2.4 RUN FAILED"}
