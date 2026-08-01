from pathlib import Path
import argparse
import hashlib
import json

def hash_json(value):
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()

parser = argparse.ArgumentParser()
parser.add_argument("--repository-root", default=".")
args = parser.parse_args()

output_root = Path(args.repository_root).resolve() / "release/v90_60/output"
certificate = json.loads(
    (output_root / "actual_paper_runtime_certificate_v90_60.json").read_text()
)
verify_document = json.loads(
    (output_root / "actual_paper_runtime_verify_v90_60.json").read_text()
)

unsigned = dict(certificate)
expected_hash = unsigned.pop("certificate_sha256")
summary = certificate["summary"]

checks = {
    "certificate_hash_valid": expected_hash == hash_json(unsigned),
    "status_pass": certificate["status"] == "PASS",
    "verify_flag_true": verify_document["verified"] is True,
    "certificate_count_two": summary["certificate_count"] == 2,
    "runtime_state_ready":
        summary["runtime_state"] == "READY_READ_ONLY",
    "integrity_pass": summary["integrity_status"] == "PASS",
    "readiness_pass": summary["readiness_status"] == "PASS",
    "audit_pass": summary["audit_status"] == "PASS",
    "certification_complete":
        certificate["actual_paper_runtime_certification_complete"] is True,
    "rc1_ready":
        certificate["actual_paper_read_only_runtime_rc1_ready"] is True,
    "replay_verified": certificate["runtime_replay_verified"] is True,
    "recovery_verified": certificate["runtime_recovery_verified"] is True,
    "restart_verified": certificate["runtime_restart_verified"] is True,
    "rollback_verified": certificate["runtime_rollback_verified"] is True,
    "scheduler_disabled": certificate["scheduler_enabled"] is False,
    "runtime_disabled": certificate["runtime_loop_enabled"] is False,
    "write_zero": certificate["write_capability_count"] == 0,
    "network_zero": certificate["network_requests_executed"] == 0,
    "orders_zero": certificate["actual_orders_submitted"] == 0,
}
failed_checks = [name for name, passed in checks.items() if not passed]

print(
    json.dumps(
        {
            "stage_range": "V90.41-V90.60",
            "status": "PASS" if not failed_checks else "FAIL",
            "release_candidate": certificate["release_candidate"],
            "checks": checks,
            "failed_checks": failed_checks,
            "next_phase": certificate["next_phase"],
        },
        indent=2,
        sort_keys=True,
    )
)
raise SystemExit(0 if not failed_checks else 1)
