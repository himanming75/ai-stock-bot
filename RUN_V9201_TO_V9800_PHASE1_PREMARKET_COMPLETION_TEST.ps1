$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
  tools.test_v9201_to_v9800_phase1_premarket_completion `
  -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS / 테스트 통과"
Write-Host "PHASE 1 PREMARKET COMPLETION: READY / 1단계 장전 완료 준비"
Write-Host "BILINGUAL REPORT: READY / 이중 언어 보고서 준비"
Write-Host "CONFIG ACTIVATION: OFF / 설정 활성화 차단"
Write-Host "COMMAND EXECUTION: OFF / 명령 실행 차단"
Write-Host "BACKUP EXECUTION: OFF / 백업 실행 차단"
Write-Host "NOTIFICATION DELIVERY: OFF / 알림 발송 차단"
Write-Host "BROKER WRITE: OFF / 브로커 주문 차단"
Write-Host "ORDER SUBMISSION: OFF / 주문 제출 차단"
