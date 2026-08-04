from pathlib import Path
import argparse, json, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from real_paper_validation.engine import evaluate

parser = argparse.ArgumentParser()
parser.add_argument("--allow-paper-network", action="store_true")
args = parser.parse_args()
print(json.dumps(evaluate(ROOT, allow_network=args.allow_paper_network), indent=2, sort_keys=True))
