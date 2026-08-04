from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.io import write_json
from autonomous_risk_governor.policy_loader import load_and_validate

parser = argparse.ArgumentParser()
parser.add_argument(
    "--policy",
    default="release/v391_01a/config/risk_governor_policy.json",
)
parser.add_argument(
    "--output",
    default="release/v391_01a/actual/risk_policy_validation_result.json",
)
args = parser.parse_args()

result = load_and_validate(ROOT / args.policy)
write_json(ROOT / args.output, result)
print(json.dumps(result, indent=2, sort_keys=True))
