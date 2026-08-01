from pathlib import Path
import argparse
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_market_data.actual_paper_runtime_certification_v90_41_60 import (
    ActualPaperRuntimeCertificationConfig,
    build_certificate,
    run_engine,
)

parser = argparse.ArgumentParser()
parser.add_argument("--repository-root", default=".")
parser.add_argument("--clean", action="store_true")
args = parser.parse_args()

repository_root = Path(args.repository_root).resolve()
output_root = repository_root / "release/v90_60/output"

if args.clean and output_root.exists():
    shutil.rmtree(output_root)

config = ActualPaperRuntimeCertificationConfig()
result = run_engine(repository_root, config, output_root)
certificate = build_certificate(output_root, config, result)

summary = {
    "stage_range": "V90.41-V90.60",
    "status": certificate["status"],
    "release_candidate": certificate["release_candidate"],
    **certificate["summary"],
    "actual_paper_runtime_certification_complete":
        certificate["actual_paper_runtime_certification_complete"],
    "actual_paper_read_only_runtime_rc1_ready":
        certificate["actual_paper_read_only_runtime_rc1_ready"],
    "runtime_integrity_verified": certificate["runtime_integrity_verified"],
    "runtime_replay_verified": certificate["runtime_replay_verified"],
    "runtime_recovery_verified": certificate["runtime_recovery_verified"],
    "runtime_restart_verified": certificate["runtime_restart_verified"],
    "runtime_rollback_verified": certificate["runtime_rollback_verified"],
    "scheduler_enabled": False,
    "runtime_loop_enabled": False,
    "write_capability_count": 0,
    "network_requests_executed": 0,
    "actual_orders_submitted": 0,
    "next_phase": certificate["next_phase"],
}
print(json.dumps(summary, indent=2, sort_keys=True))
raise SystemExit(0 if certificate["status"] == "PASS" else 1)
