$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python=if(Test-Path ".\.venv\Scripts\python.exe"){
    ".\.venv\Scripts\python.exe"
}else{
    "python"
}

& $Python -c "import sys;sys.path.insert(0,'.');from dashboard.operations_dashboard_v3_2 import build_status;from pathlib import Path;s=build_status(Path(r'C:\stock-bot'));v=s['visualization'];assert s['contracts']['read_only'];assert v['contracts']['read_only'];assert not v['contracts']['broker_write_performed'];assert not v['contracts']['order_submission_performed'];print('STATUS BUILD: PASS');print('VISUALIZATION STATUS:',s['visualization_status']);print('EQUITY POINTS:',v['summary']['equity_point_count']);print('DAILY PNL POINTS:',v['summary']['daily_realized_point_count']);print('POSITION ALLOCATION:',v['position_allocation']);print('VALIDATION SLOTS:',len(v['validation_slots']));print('CURRENT UNREALIZED:',v['summary']['current_unrealized_pnl'])"
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "VERIFY: PASS"
