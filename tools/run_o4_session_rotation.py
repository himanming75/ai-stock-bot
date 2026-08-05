from datetime import date
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from operations.session_rotation import rotate_session

parser = argparse.ArgumentParser()
parser.add_argument("--trading-day", default=date.today().isoformat())
parser.add_argument("--reason", default="OPERATOR_PREPARED_SESSION")
args = parser.parse_args()

result = rotate_session(
    ROOT,
    trading_day=args.trading_day,
    reason=args.reason,
)
print(json.dumps(result, indent=2, sort_keys=True))
