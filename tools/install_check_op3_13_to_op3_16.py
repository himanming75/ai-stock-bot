from pathlib import Path
R=["autonomous_paper_runtime/limited_autonomous_paper_trading.py","tools/run_limited_autonomous_paper_trading_op3_13_to_op3_16.py","tools/test_limited_autonomous_paper_trading_op3_13_to_op3_16.py","tools/install_check_op3_13_to_op3_16.py","tools/verify_limited_autonomous_paper_trading_op3_13_to_op3_16.py","RUN_OP3_13_TO_OP3_16_LIMITED_AUTONOMOUS_PAPER.ps1","RUN_OP3_13_TO_OP3_16_TEST_AND_VERIFY.ps1","OP3_13_TO_OP3_16_MANIFEST.json"]
root=Path(__file__).resolve().parents[1];m=[x for x in R if not(root/x).exists()]
if m:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(m))
print("INSTALL_CHECK=PASS")
