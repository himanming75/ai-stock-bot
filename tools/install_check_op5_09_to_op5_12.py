from pathlib import Path
R=[
"paper_pilot/validation_certificate.py",
"dashboard/validation_certificate_integration.py",
"tools/run_validation_certificate_op5_09_to_op5_12.py",
"tools/test_validation_certificate_op5_09_to_op5_12.py",
"tools/install_check_op5_09_to_op5_12.py",
"tools/verify_validation_certificate_op5_09_to_op5_12.py",
"RUN_OP5_09_TO_OP5_12_CERTIFICATE.ps1",
"RUN_OP5_09_TO_OP5_12_TEST_AND_VERIFY.ps1",
"OP5_09_TO_OP5_12_MANIFEST.json"]
root=Path(__file__).resolve().parents[1]
missing=[x for x in R if not(root/x).exists()]
if missing:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
