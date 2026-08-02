from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.final_validation_release_bundle import (
    FinalValidationReleaseBundle,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    result = FinalValidationReleaseBundle().run(
        stability_result_path=root/"release/v141_01_to_v141_05/actual/operational_stability_bundle_result.json",
        stability_token_path=root/"release/v141_01_to_v141_05/actual/operational_stability_token.json",
        multi_day_snapshot_path=root/"release/v141_06_to_v141_08/input/multi_day_stability_snapshot.json",
        failure_injection_snapshot_path=root/"release/v141_06_to_v141_08/input/failure_injection_snapshot.json",
        deployment_readiness_snapshot_path=root/"release/v141_06_to_v141_08/input/deployment_readiness_snapshot.json",
        validation_certificate_path=root/"release/v141_06_to_v141_08/actual/multi_day_validation_certificate.json",
        failure_certificate_path=root/"release/v141_06_to_v141_08/actual/failure_injection_certificate.json",
        release_manifest_path=root/"release/v141_06_to_v141_08/actual/paper_production_release_manifest.json",
        production_token_path=root/"release/v141_06_to_v141_08/actual/paper_production_release_token.json",
        result_path=root/"release/v141_06_to_v141_08/actual/final_validation_release_result.json",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={result['result_path']}")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
