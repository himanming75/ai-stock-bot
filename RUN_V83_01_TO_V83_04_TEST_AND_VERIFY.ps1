$ErrorActionPreference='Stop'; Set-Location $PSScriptRoot
python tools/install_check_v83_01_to_v83_04.py; if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_automated_orchestrator_v83_01_to_v83_04 -v; if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V83_01_TO_V83_04_AUTOMATED_ORCHESTRATOR.ps1; if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_automated_orchestrator_v83_01_to_v83_04.py; if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host 'V83.01-V83.04 TEST AND VERIFY PASS'
