from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"shadow_runtime/autonomous_cycle_v82_01_04.py",
"dashboard/autonomous_shadow_cycle_integration.py",
"tools/run_autonomous_shadow_cycle_v82_01_to_v82_04.py",
"tools/test_autonomous_shadow_cycle_v82_01_to_v82_04.py",
"tools/install_check_v82_01_to_v82_04.py",
"tools/verify_autonomous_shadow_cycle_v82_01_to_v82_04.py",
"RUN_V82_01_TO_V82_04_AUTONOMOUS_SHADOW_CYCLE.ps1",
"RUN_V82_01_TO_V82_04_TEST_AND_VERIFY.ps1",
"V82_01_TO_V82_04_MANIFEST.json"]
missing=[x for x in required if not (ROOT/x).exists()]
if missing: raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
