from pathlib import Path
R=[
"autonomous_paper_runtime/shadow_performance_evaluation.py",
"tools/run_shadow_performance_evaluation_op2_05_to_op2_08.py",
"tools/test_shadow_performance_evaluation_op2_05_to_op2_08.py",
"tools/install_check_op2_05_to_op2_08.py",
"tools/verify_shadow_performance_evaluation_op2_05_to_op2_08.py",
"RUN_OP2_05_TO_OP2_08_SHADOW_PERFORMANCE.ps1",
"RUN_OP2_05_TO_OP2_08_TEST_AND_VERIFY.ps1",
"OP2_05_TO_OP2_08_MANIFEST.json"]
root=Path(__file__).resolve().parents[1]
missing=[x for x in R if not(root/x).exists()]
if missing:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
