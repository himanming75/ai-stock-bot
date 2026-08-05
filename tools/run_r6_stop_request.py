from argparse import ArgumentParser
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_session.service import request_stop

parser = ArgumentParser()
parser.add_argument("--reason", default="OPERATOR_REQUEST")
args = parser.parse_args()

result = request_stop(ROOT, args.reason)
print(json.dumps(result, indent=2, sort_keys=True))
