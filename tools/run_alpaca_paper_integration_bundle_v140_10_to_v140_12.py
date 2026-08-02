from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.alpaca_paper_integration_bundle import (
    AlpacaPaperIntegrationBundle,
    PAPER_BASE_URL,
)

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", default=".")
    p.add_argument("--base-url", default=PAPER_BASE_URL)
    p.add_argument("--enable-network", action="store_true")
    p.add_argument("--enable-submission", action="store_true")
    p.add_argument("--approval-phrase", default="")
    a = p.parse_args()
    root = Path(a.repository_root).resolve()
    result = AlpacaPaperIntegrationBundle().run(
        engine_result_path=root/"release/v140_06_to_v140_09/actual/autonomous_engine_bundle_result.json",
        engine_token_path=root/"release/v140_06_to_v140_09/actual/autonomous_engine_token.json",
        order_candidate_path=root/"release/v140_06_to_v140_09/actual/order_candidate.json",
        local_broker_snapshot_path=root/"release/v140_10_to_v140_12/input/local_paper_broker_snapshot.json",
        reconciliation_snapshot_path=root/"release/v140_10_to_v140_12/input/reconciliation_snapshot.json",
        read_result_path=root/"release/v140_10_to_v140_12/actual/paper_broker_read_result.json",
        submission_result_path=root/"release/v140_10_to_v140_12/actual/paper_submission_result.json",
        reconciliation_result_path=root/"release/v140_10_to_v140_12/actual/paper_reconciliation_result.json",
        final_result_path=root/"release/v140_10_to_v140_12/actual/alpaca_paper_integration_bundle_result.json",
        base_url=a.base_url,
        enable_network=a.enable_network,
        enable_submission=a.enable_submission,
        approval_phrase=a.approval_phrase,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={result['result_path']}")
    return 0 if result["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
