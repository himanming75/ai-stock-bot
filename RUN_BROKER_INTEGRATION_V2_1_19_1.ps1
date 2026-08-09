$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

Write-Host "=== BROKER INTEGRATION V2.1.19.1 ==="

& $Python -m compileall -q .\broker_integration_v1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\tests\test_canonical_paper_gate_semantic_correction_v2_1_19_1.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\tests\test_evidence_qualification_sandbox_readiness_gate_v2_1_17.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\tests\test_manual_sandbox_review_packet_builder_v2_1_18.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\tests\test_manual_approval_record_expiration_guard_v2_1_19.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
