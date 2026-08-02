from pathlib import Path

REQUIRED = [
    "autonomous_paper_runtime/terminal_commit_handoff.py",
    "tools/run_terminal_commit_handoff_v139_02.py",
    "tools/test_terminal_commit_handoff_v139_02.py",
    "tools/verify_terminal_commit_handoff_v139_02.py",
    "RUN_V139_02_TERMINAL_COMMIT_HANDOFF.ps1",
    "RUN_V139_02_TEST_AND_VERIFY.ps1",
    "V139_02_BUNDLE_MANIFEST.json",
]

root = Path(__file__).resolve().parents[1]
missing = [path for path in REQUIRED if not (root / path).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
