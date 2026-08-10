$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
& "$Repo\.venv\Scripts\python.exe" -m ai_engine_v2.challenger_shadow_execution_simulator_cli_v2_2_7 --root $Repo
if($LASTEXITCODE -ne 0){throw "V2.2.7 RUN FAILED"}
