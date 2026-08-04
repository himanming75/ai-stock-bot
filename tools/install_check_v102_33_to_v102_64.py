from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

required = [
    "autonomous_decision/io.py",
    "autonomous_decision/signals.py",
    "autonomous_decision/conflicts.py",
    "autonomous_decision/veto.py",
    "autonomous_decision/confidence.py",
    "autonomous_decision/decision.py",
    "autonomous_decision/approval.py",
    "autonomous_decision/engine.py",
    "autonomous_decision/dashboard.py",
    "tools/run_v102_33_to_v102_64.py",
    "tools/test_v102_33_to_v102_64.py",
    "tools/verify_v102_33_to_v102_64.py",
    "release/v102_33_to_v102_64/input/autonomous_decision_policy.json",
]
missing = [item for item in required if not (ROOT / item).exists()]
for item in missing:
    print("MISSING:", item)
if missing:
    raise SystemExit(1)

print("V102.33-V102.64 INSTALL CHECK PASS")
