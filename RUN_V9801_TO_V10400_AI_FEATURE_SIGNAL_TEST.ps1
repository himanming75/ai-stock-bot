[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
  tools.test_v9801_to_v10400_ai_feature_signal `
  -v

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

Write-Host "TEST: PASS / 테스트 통과"
Write-Host "AI FEATURE ENGINE: READY / AI 특징 엔진 준비"
Write-Host "SIGNAL CANDIDATES: READY / 신호 후보 준비"
Write-Host "BROKER WRITE: OFF / 브로커 주문 차단"
Write-Host "ORDER SUBMISSION: OFF / 주문 제출 차단"
