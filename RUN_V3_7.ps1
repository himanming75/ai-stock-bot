$ErrorActionPreference="Stop"; Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
& $Python .\dashboard\patch_v3_7_normalizer_identifiers.py --root C:\stock-bot; if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Python .\dashboard\patch_trade_analytics_v3_7.py --root C:\stock-bot; if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Python -m py_compile .\dashboard\trade_ledger_normalizer_v3_6.py .\dashboard\trade_analytics_v3_5.py .\dashboard\cross_ledger_trade_reconstruction_v3_7.py .\dashboard\audit_cross_ledger_reconstruction_v3_7.py; if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Python -m unittest .\tests\test_cross_ledger_reconstruction_v3_7.py; if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Python .\dashboard\audit_cross_ledger_reconstruction_v3_7.py --root C:\stock-bot --write; if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "RUN: PASS"
