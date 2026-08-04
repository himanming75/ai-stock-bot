from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

required = [
    "adaptive_rebalance/io.py",
    "adaptive_rebalance/regime.py",
    "adaptive_rebalance/costs.py",
    "adaptive_rebalance/thresholds.py",
    "adaptive_rebalance/optimizer.py",
    "adaptive_rebalance/stability.py",
    "adaptive_rebalance/gate.py",
    "adaptive_rebalance/engine.py",
    "adaptive_rebalance/dashboard.py",
    "tools/run_v101_33_to_v101_64.py",
    "tools/test_v101_33_to_v101_64.py",
    "tools/verify_v101_33_to_v101_64.py",
    "release/v101_33_to_v101_64/input/adaptive_rebalance_policy.json",
]
missing = [item for item in required if not (ROOT / item).exists()]
for item in missing:
    print("MISSING:", item)
if missing:
    raise SystemExit(1)

for dependency in ("portfolio_rebalance_control", "risk_budget"):
    if not (ROOT / dependency).exists():
        print("MISSING DEPENDENCY:", dependency)
        raise SystemExit(1)

print("V101.33-V101.64 INSTALL CHECK PASS")
