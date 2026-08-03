from pathlib import Path
R=['paper_pilot/paper_trading_completion.py','dashboard/paper_trading_completion_integration.py','tools/run_paper_trading_completion_v80_01_to_v80_04.py','tools/test_paper_trading_completion_v80_01_to_v80_04.py','tools/install_check_v80_01_to_v80_04.py','tools/verify_paper_trading_completion_v80_01_to_v80_04.py','RUN_V80_01_TO_V80_04_COMPLETION.ps1','RUN_V80_01_TO_V80_04_TEST_AND_VERIFY.ps1','V80_01_TO_V80_04_MANIFEST.json']
r=Path(__file__).resolve().parents[1];m=[x for x in R if not(r/x).exists()]
if m:raise SystemExit('INSTALL_CHECK=FAIL missing='+','.join(m))
print('INSTALL_CHECK=PASS')
