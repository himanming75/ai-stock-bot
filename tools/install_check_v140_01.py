from pathlib import Path
REQUIRED = [
    "autonomous_paper_runtime/autonomous_runtime_supervisor.py",
    "tools/run_autonomous_runtime_supervisor_v140_01.py",
    "tools/test_autonomous_runtime_supervisor_v140_01.py",
    "tools/verify_autonomous_runtime_supervisor_v140_01.py",
    "RUN_V140_01_AUTONOMOUS_RUNTIME_SUPERVISOR.ps1",
    "RUN_V140_01_TEST_AND_VERIFY.ps1",
    "V140_01_BUNDLE_MANIFEST.json",
]
root = Path(__file__).resolve().parents[1]
missing = [x for x in REQUIRED if not (root / x).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
