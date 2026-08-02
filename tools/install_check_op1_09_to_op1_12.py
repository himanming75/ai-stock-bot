from pathlib import Path
R=["autonomous_paper_runtime/weekly_observation_review.py","tools/run_weekly_observation_review_op1_09_to_op1_12.py","tools/test_weekly_observation_review_op1_09_to_op1_12.py","tools/install_check_op1_09_to_op1_12.py","tools/verify_weekly_observation_review_op1_09_to_op1_12.py","RUN_OP1_09_TO_OP1_12_WEEKLY_REVIEW.ps1","RUN_OP1_09_TO_OP1_12_TEST_AND_VERIFY.ps1","OP1_09_TO_OP1_12_MANIFEST.json"]
root=Path(__file__).resolve().parents[1];m=[x for x in R if not(root/x).exists()]
if m:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(m))
print("INSTALL_CHECK=PASS")
