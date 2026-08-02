from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.operational_stability_bundle import (
    OperationalStabilityBundle,
)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    result = OperationalStabilityBundle().run(
        integration_result_path=root/"release/v140_10_to_v140_12/actual/alpaca_paper_integration_bundle_result.json",
        health_snapshot_path=root/"release/v141_01_to_v141_05/input/operational_health_snapshot.json",
        retry_policy_path=root/"release/v141_01_to_v141_05/input/retry_rate_limit_policy.json",
        daily_audit_path=root/"release/v141_01_to_v141_05/actual/daily_audit_report.json",
        process_lock_path=root/"release/v141_01_to_v141_05/actual/operational_stability_lock.json",
        integrity_ledger_path=root/"release/v141_01_to_v141_05/actual/integrity_ledger.jsonl",
        health_result_path=root/"release/v141_01_to_v141_05/actual/operational_health_result.json",
        stability_token_path=root/"release/v141_01_to_v141_05/actual/operational_stability_token.json",
        result_path=root/"release/v141_01_to_v141_05/actual/operational_stability_bundle_result.json",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={result['result_path']}")
    return 0 if result["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
