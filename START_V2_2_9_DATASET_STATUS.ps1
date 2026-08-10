$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
& "$Repo\.venv\Scripts\python.exe" -m ai_engine_v2.training_dataset_builder_cli_v2_2_9 --root $Repo --mode status
if($LASTEXITCODE -ne 0){throw "V2.2.9 STATUS FAILED"}
