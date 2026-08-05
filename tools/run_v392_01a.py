from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.io import append_jsonl, read_json, write_json
from execution_authorization.authorization_guard import run_authorization
from execution_authorization.token import canonical_hash

parser = argparse.ArgumentParser()
parser.add_argument(
    "--policy",
    default="release/v392_01a/config/execution_authorization_policy.json",
)
parser.add_argument(
    "--risk-result",
    default="release/v392_01a/fixtures/sample_risk_result.json",
)
parser.add_argument(
    "--proposal",
    default="release/v392_01a/fixtures/sample_proposal.json",
)
parser.add_argument(
    "--request",
    default="release/v392_01a/fixtures/sample_authorization_request.json",
)
parser.add_argument(
    "--output",
    default="release/v392_01a/actual/execution_authorization_result.json",
)
args = parser.parse_args()

policy = read_json(ROOT / args.policy)
risk_result = read_json(ROOT / args.risk_result)
proposal = read_json(ROOT / args.proposal)
request = read_json(ROOT / args.request)

# Fixture convenience: replace placeholders with actual hashes.
if request.get("proposal_hash") == "__AUTO__":
    request["proposal_hash"] = canonical_hash(proposal)
if request.get("policy_hash") == "__AUTO__":
    request["policy_hash"] = risk_result.get("policy_hash")

result = run_authorization(policy, risk_result, proposal, request)
write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v392_01a/actual/execution_authorization_ledger.jsonl",
    result,
)
print(json.dumps(result, indent=2, sort_keys=True))
