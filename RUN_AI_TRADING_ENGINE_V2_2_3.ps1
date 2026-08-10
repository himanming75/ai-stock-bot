$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
& "$Repo\.venv\Scripts\python.exe" -m ai_engine_v2.performance_segmentation_feature_attribution_cli_v2_2_3 --root $Repo
if($LASTEXITCODE -ne 0){throw "V2.2.3 RUN FAILED"}
