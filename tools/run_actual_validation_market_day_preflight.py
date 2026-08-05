from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validation_control.preflight import run_market_day_preflight

result = run_market_day_preflight(ROOT)
path = (
    ROOT / "release/actual_validation_control_center/actual/"
           "market_day_preflight.json"
)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(result, indent=2, sort_keys=True))
