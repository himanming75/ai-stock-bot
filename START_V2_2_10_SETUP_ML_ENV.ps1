$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$MlVenv="$Repo\.venv_ml"

Write-Host "V2.2.10 ISOLATED ML ENVIRONMENT"
Write-Host "Existing trading .venv will NOT be modified."

if(-not (Test-Path "$MlVenv\Scripts\python.exe")){
    & "$Repo\.venv\Scripts\python.exe" -m venv $MlVenv
    if($LASTEXITCODE -ne 0){throw "CREATE .venv_ml FAILED"}
}

$MlPython="$MlVenv\Scripts\python.exe"

$Check=& $MlPython -c "import sklearn, joblib, numpy; print('READY')" 2>$null
if($LASTEXITCODE -ne 0){
    Write-Host "Installing ML dependencies into .venv_ml only..."
    & $MlPython -m pip install --upgrade pip
    if($LASTEXITCODE -ne 0){throw "ML PIP UPGRADE FAILED"}
    & $MlPython -m pip install scikit-learn joblib
    if($LASTEXITCODE -ne 0){throw "ML DEPENDENCY INSTALL FAILED"}
}

& $MlPython -c "import sklearn, joblib, numpy; print('ML ENV: READY'); print('scikit-learn:', sklearn.__version__)"
if($LASTEXITCODE -ne 0){throw "ML ENV VERIFY FAILED"}
