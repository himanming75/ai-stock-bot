from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from operations.operator_checklist import build_operator_checklist

result = build_operator_checklist(ROOT)
print(json.dumps(result, indent=2, sort_keys=True))
