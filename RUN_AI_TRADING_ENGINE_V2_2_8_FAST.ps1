$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
& "$Repo\.venv\Scripts\python.exe" -m ai_engine_v2.fast_data_acceleration_cli_v2_2_8 --root $Repo --mode status
if($LASTEXITCODE -ne 0){throw "V2.2.8 FAST STATUS FAILED"}
