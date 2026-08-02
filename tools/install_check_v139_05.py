from pathlib import Path
REQUIRED = [
    "autonomous_paper_runtime/autonomous_cycle_resume.py",
    "tools/run_autonomous_cycle_resume_v139_05.py",
    "tools/test_autonomous_cycle_resume_v139_05.py",
    "tools/verify_autonomous_cycle_resume_v139_05.py",
    "RUN_V139_05_AUTONOMOUS_CYCLE_RESUME.ps1",
    "RUN_V139_05_TEST_AND_VERIFY.ps1",
    "V139_05_BUNDLE_MANIFEST.json",
]
root = Path(__file__).resolve().parents[1]
missing = [item for item in REQUIRED if not (root / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
