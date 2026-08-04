from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

required = [
    "daily_paper_runner/io.py",
    "daily_paper_runner/session.py",
    "daily_paper_runner/preflight.py",
    "daily_paper_runner/approval.py",
    "daily_paper_runner/plan.py",
    "daily_paper_runner/dedup.py",
    "daily_paper_runner/checkpoint.py",
    "daily_paper_runner/report.py",
    "daily_paper_runner/engine.py",
    "daily_paper_runner/dashboard.py",
    "tools/run_v106_01_to_v106_32.py",
    "tools/test_v106_01_to_v106_32.py",
    "tools/verify_v106_01_to_v106_32.py",
    "release/v106_01_to_v106_32/input/daily_paper_runner_policy.json",
]
missing = [item for item in required if not (ROOT / item).exists()]
for item in missing:
    print("MISSING:", item)
if missing:
    raise SystemExit(1)

print("V106.01-V106.32 INSTALL CHECK PASS")
