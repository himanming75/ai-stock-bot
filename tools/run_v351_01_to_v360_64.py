from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_order_proposal.engine import build_proposal
from paper_order_proposal.io import append_jsonl, read_json, write_json
from paper_order_proposal.policy import load, validate

parser = argparse.ArgumentParser()
parser.add_argument("--decision", default="release/v341_01_to_v350_64/actual/latest_governed_decision.json")
parser.add_argument("--runtime", default="release/v351_01_to_v360_64/fixtures/sample_runtime_context.json")
parser.add_argument("--output", default="release/v351_01_to_v360_64/actual/latest_paper_order_proposal.json")
parser.add_argument("--no-ledger", action="store_true")
args = parser.parse_args()

policy = load(ROOT)
validation = validate(policy)
if not validation["valid"]:
    raise SystemExit("INVALID_POLICY:" + ",".join(validation["failed"]))

result = build_proposal(
    read_json(ROOT / args.decision),
    read_json(ROOT / args.runtime),
    policy,
)
write_json(ROOT / args.output, result)
if not args.no_ledger:
    append_jsonl(ROOT / "release/v351_01_to_v360_64/actual/paper_order_proposal_ledger.jsonl", result)
print(json.dumps(result, indent=2, sort_keys=True))
