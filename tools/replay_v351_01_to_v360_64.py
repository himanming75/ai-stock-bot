from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_order_proposal.io import read_json
from paper_order_proposal.replay import verify

parser = argparse.ArgumentParser()
parser.add_argument("--input", default="release/v351_01_to_v360_64/actual/latest_paper_order_proposal.json")
args = parser.parse_args()

result = verify(read_json(ROOT / args.input))
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["valid"] else 1)
