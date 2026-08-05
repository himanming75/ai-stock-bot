from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from operations.metrics import collect_metrics

print(json.dumps(collect_metrics(ROOT), indent=2, sort_keys=True))
