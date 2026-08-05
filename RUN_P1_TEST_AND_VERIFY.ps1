$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Python=Join-Path $Root ".venv\Scripts\python.exe"
if(-not(Test-Path $Python)){$Python="python"}
$Old=$env:PYTHONPATH
try{$env:PYTHONPATH=$Root;Write-Host "=== P1 UNIT TEST ===";& $Python -m unittest tools.test_p1_broker_consolidation -v;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE};Write-Host "=== P1 RUN ===";& $Python (Join-Path $Root "tools\run_p1_broker_consolidation.py");if($LASTEXITCODE-ne 0){exit $LASTEXITCODE};Write-Host "=== P1 VERIFY ===";& $Python (Join-Path $Root "tools\verify_p1_broker_consolidation.py");exit $LASTEXITCODE}finally{$env:PYTHONPATH=$Old}
