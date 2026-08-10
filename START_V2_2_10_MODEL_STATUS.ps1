$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo

$Python="$Repo\.venv_ml\Scripts\python.exe"
if(-not (Test-Path $Python)){
    $Python="$Repo\.venv\Scripts\python.exe"
}
$env:PYTHONPATH=$Repo

& $Python -m ai_engine_v2.ml_model_training_validation_cli_v2_2_10 `
 --root $Repo --mode status
if($LASTEXITCODE -ne 0){throw "V2.2.10 STATUS FAILED"}
