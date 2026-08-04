from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "autonomous_paper_session/io.py",
    "autonomous_paper_session/config.py",
    "autonomous_paper_session/lock.py",
    "autonomous_paper_session/stop.py",
    "autonomous_paper_session/checkpoint.py",
    "autonomous_paper_session/runner.py",
    "autonomous_paper_session/dashboard.py",
    "web_controller/autonomous_paper_session_api.py",
    "tools/run_v261_01_to_v265_64.py",
    "tools/test_v261_01_to_v265_64.py",
    "tools/verify_v261_01_to_v265_64.py",
    "release/v261_01_to_v265_64/config/session_runner_policy.json",
    "release/v261_01_to_v265_64/docs/AUTONOMOUS_PAPER_SESSION_RUNNER_GUIDE.md",
]
missing = [item for item in required if not (ROOT / item).exists()]
for item in missing:
    print("MISSING:", item)
if missing:
    raise SystemExit(1)
print("V261.01-V265.64 INSTALL CHECK PASS")
