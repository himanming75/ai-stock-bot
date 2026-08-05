from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from operations.l1_safety import load_live_safety_policy

result = load_live_safety_policy().evaluate()
out = (
    ROOT
    / "release/operations_bundle/actual/"
      "l1_safety_preparation_result.json"
)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["status"] == "PASS" else 1)
