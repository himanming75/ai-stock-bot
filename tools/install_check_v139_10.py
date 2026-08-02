from pathlib import Path

REQUIRED = [
    "autonomous_paper_runtime/terminal_commit_cycle_completion.py",
    "tools/run_terminal_commit_cycle_completion_v139_10.py",
    "tools/test_terminal_commit_cycle_completion_v139_10.py",
    "tools/verify_terminal_commit_cycle_completion_v139_10.py",
    "RUN_V139_10_TERMINAL_COMMIT_CYCLE_COMPLETION.ps1",
    "RUN_V139_10_TEST_AND_VERIFY.ps1",
    "V139_10_BUNDLE_MANIFEST.json",
]

root = Path(__file__).resolve().parents[1]
missing = [item for item in REQUIRED if not (root / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
