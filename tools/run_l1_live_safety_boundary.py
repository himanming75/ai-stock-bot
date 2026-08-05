from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from live_safety.boundary import evaluate_live_boundary

result = evaluate_live_boundary(ROOT)
path = ROOT / "release/l1_live_safety_boundary/actual/l1_result.json"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["status"] == "PASS" else 1)
