from pathlib import Path

REQUIRED = [
    "autonomous_paper_runtime/shadow_daily_automation.py",
    "tools/run_shadow_daily_automation_op2_17_to_op2_20.py",
    "tools/test_shadow_daily_automation_op2_17_to_op2_20.py",
    "tools/install_check_op2_17_to_op2_20.py",
    "tools/verify_shadow_daily_automation_op2_17_to_op2_20.py",
    "RUN_OP2_17_TO_OP2_20_SHADOW_DAILY_AUTOMATION.ps1",
    "RUN_OP2_17_TO_OP2_20_TEST_AND_VERIFY.ps1",
    "OP2_17_TO_OP2_20_MANIFEST.json",
]

root = Path(__file__).resolve().parents[1]
missing = [item for item in REQUIRED if not (root/item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
