from pathlib import Path
import argparse, json, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from real_paper_data_collection.collector import collect
from real_paper_data_collection.session import run

parser = argparse.ArgumentParser()
parser.add_argument("--allow-paper-network", action="store_true")
parser.add_argument("--session", action="store_true")
parser.add_argument("--no-sleep", action="store_true")
args = parser.parse_args()

if args.session:
    result = run(
        ROOT,
        allow_network=args.allow_paper_network,
        sleep_enabled=not args.no_sleep,
    )
else:
    result = collect(ROOT, allow_network=args.allow_paper_network)

print(json.dumps(result, indent=2, sort_keys=True))
