from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

required = [
    "autonomous_cycle/io.py",
    "autonomous_cycle/model.py",
    "autonomous_cycle/identity.py",
    "autonomous_cycle/dedup.py",
    "autonomous_cycle/lock.py",
    "autonomous_cycle/checkpoint.py",
    "autonomous_cycle/retry.py",
    "autonomous_cycle/executor.py",
    "autonomous_cycle/state.py",
    "autonomous_cycle/engine.py",
    "autonomous_cycle/dashboard.py",
    "tools/run_v103_01_to_v103_32.py",
    "tools/test_v103_01_to_v103_32.py",
    "tools/verify_v103_01_to_v103_32.py",
    "release/v103_01_to_v103_32/input/autonomous_cycle_policy.json",
]
missing = [item for item in required if not (ROOT / item).exists()]
for item in missing:
    print("MISSING:", item)
if missing:
    raise SystemExit(1)

print("V103.01-V103.32 INSTALL CHECK PASS")
