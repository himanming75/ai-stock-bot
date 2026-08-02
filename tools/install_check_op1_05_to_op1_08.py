from pathlib import Path
REQUIRED = [
    "autonomous_paper_runtime/daily_read_only_observation.py",
    "tools/run_daily_read_only_observation_op1_05_to_op1_08.py",
    "tools/test_daily_read_only_observation_op1_05_to_op1_08.py",
    "tools/install_check_op1_05_to_op1_08.py",
    "tools/verify_daily_read_only_observation_op1_05_to_op1_08.py",
    "RUN_OP1_05_TO_OP1_08_DAILY_OBSERVATION.ps1",
    "RUN_OP1_05_TO_OP1_08_TEST_AND_VERIFY.ps1",
    "OP1_05_TO_OP1_08_MANIFEST.json",
]
root = Path(__file__).resolve().parents[1]
missing = [x for x in REQUIRED if not (root/x).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
