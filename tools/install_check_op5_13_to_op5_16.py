from pathlib import Path
R=[
"paper_pilot/promotion_gate.py",
"dashboard/promotion_gate_integration.py",
"tools/run_promotion_gate_op5_13_to_op5_16.py",
"tools/test_promotion_gate_op5_13_to_op5_16.py",
"tools/install_check_op5_13_to_op5_16.py",
"tools/verify_promotion_gate_op5_13_to_op5_16.py",
"RUN_OP5_13_TO_OP5_16_PROMOTION_GATE.ps1",
"RUN_OP5_13_TO_OP5_16_TEST_AND_VERIFY.ps1",
"OP5_13_TO_OP5_16_MANIFEST.json"]
root=Path(__file__).resolve().parents[1]
missing=[x for x in R if not(root/x).exists()]
if missing:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
