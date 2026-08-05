from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from operations_v2.service import run_operations_v2

result = run_operations_v2(ROOT)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["status"] == "PASS" else 1)
