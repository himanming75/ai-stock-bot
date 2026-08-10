$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"
& $Python -m ai_engine_v2.ml_research_readiness_cli_v2_2_13 --root $Repo --mode evaluate
if($LASTEXITCODE -ne 0){throw "V2.2.13 EVALUATE FAILED"}
