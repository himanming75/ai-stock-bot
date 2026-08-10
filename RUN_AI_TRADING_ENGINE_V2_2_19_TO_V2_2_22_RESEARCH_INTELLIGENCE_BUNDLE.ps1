$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
& "$Repo\.venv\Scripts\python.exe" -m ai_engine_v2.ml_research_intelligence_bundle_cli_v2_2_19_22
if($LASTEXITCODE -ne 0){throw "V2.2.19-22 BUNDLE FAILED"}
