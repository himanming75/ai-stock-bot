from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from operations.graceful_shutdown import write_shutdown_marker

parser = argparse.ArgumentParser()
parser.add_argument("--runtime-id", default="operator-session")
parser.add_argument("--reason", default="OPERATOR_STOP")
parser.add_argument("--last-cycle-number", type=int, default=0)
args = parser.parse_args()

result = write_shutdown_marker(
    ROOT,
    runtime_id=args.runtime_id,
    reason=args.reason,
    last_cycle_number=args.last_cycle_number,
)
print(json.dumps(result, indent=2, sort_keys=True))
