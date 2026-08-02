from pathlib import Path
R=["autonomous_paper_runtime/multi_day_shadow_validation.py","tools/run_multi_day_shadow_validation_op2_09_to_op2_12.py","tools/test_multi_day_shadow_validation_op2_09_to_op2_12.py","tools/install_check_op2_09_to_op2_12.py","tools/verify_multi_day_shadow_validation_op2_09_to_op2_12.py","RUN_OP2_09_TO_OP2_12_MULTI_DAY_SHADOW.ps1","RUN_OP2_09_TO_OP2_12_TEST_AND_VERIFY.ps1","OP2_09_TO_OP2_12_MANIFEST.json"]
root=Path(__file__).resolve().parents[1];m=[x for x in R if not(root/x).exists()]
if m:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(m))
print("INSTALL_CHECK=PASS")
