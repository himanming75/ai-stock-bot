from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from broker_integration.actual_validation import validation_status

value = validation_status(ROOT)
value.update({
    "paper_complete": False,
    "live_complete": False,
})
print(json.dumps(value, indent=2, sort_keys=True))
