from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from operations.resource_trends import append_resource_sample

result = append_resource_sample(
    ROOT / "release/o3_autonomous_operations/actual/resource_trends.jsonl"
)
print(json.dumps(result, indent=2, sort_keys=True))
