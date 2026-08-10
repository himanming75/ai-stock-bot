$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python -m ai_engine_v2.ml_confidence_calibration_cli_v2_2_14 --root $Repo --mode evaluate
if($LASTEXITCODE -ne 0){throw "V2.2.14 CALIBRATION EVALUATION FAILED"}
