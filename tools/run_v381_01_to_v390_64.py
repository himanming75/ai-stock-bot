from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from portfolio_sync_recovery.engine import run
from portfolio_sync_recovery.io import read_json

parser = argparse.ArgumentParser()
parser.add_argument("--allow-paper-network", action="store_true")
args = parser.parse_args()

policy = read_json(
    ROOT / "release/v381_01_to_v390_64/config/portfolio_sync_policy.json"
)
result = run(
    ROOT,
    policy=policy,
    allow_network=args.allow_paper_network,
)
print(json.dumps(result, indent=2, sort_keys=True))
