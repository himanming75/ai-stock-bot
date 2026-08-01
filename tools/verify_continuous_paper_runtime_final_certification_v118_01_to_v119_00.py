from pathlib import Path
import argparse
import hashlib
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    output = Path(args.repository_root).resolve() / "release" / "v119_00" / "output"
    result = json.loads(
        (output / "continuous_paper_runtime_final_certification_result.json")
        .read_text(encoding="utf-8")
    )
    certificate = json.loads(
        (output / "continuous_paper_runtime_final_certificate.json")
        .read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (output / "continuous_paper_runtime_final_release_manifest.json")
        .read_text(encoding="utf-8")
    )

    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "CONTINUOUS_PAPER_RUNTIME_FINAL_CERTIFICATION",
        "certified_release": result["certified_release"] == "CONTINUOUS_PAPER_RUNTIME_CERTIFIED_V119",
        "check_count_nine": result["check_count"] == 9,
        "all_checks_passed": result["passed_check_count"] == 9,
        "stress_1000": result["stress_cycles"] == 1000,
        "restarts_nine": result["restart_count"] == 9,
        "recoveries_nine": result["recovery_count"] == 9,
        "events_1013": result["event_count"] == 1013,
        "state_consistent": result["state_consistent"] is True,
        "event_order_consistent": result["event_order_consistent"] is True,
        "recovery_consistent": result["recovery_consistent"] is True,
        "portfolio_consistent": result["portfolio_consistent"] is True,
        "certificate_exists": result["certificate_file_exists"] is True,
        "manifest_exists": result["release_manifest_exists"] is True,
        "certificate_id_match": result["certificate_id"] == certificate["certificate_id"],
        "certificate_hash_match": result["certificate_sha256"] == certificate["certificate_sha256"],
        "manifest_certificate_match": manifest["certificate_id"] == result["certificate_id"],
        "manifest_hash_match": manifest["certificate_sha256"] == result["certificate_sha256"],
        "network_zero": result["network_requests_executed"] == 0,
        "write_zero": result["write_requests_executed"] == 0,
        "paper_orders_zero": result["actual_paper_orders_submitted"] == 0,
        "live_zero": result["live_orders_submitted"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    verify = {
        "stage_range": "V118.01-V119.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "certificate_id": result["certificate_id"],
        "certificate_sha256": result["certificate_sha256"],
        "certified_release": result["certified_release"],
        "next_phase": result["next_phase"],
    }
    print(json.dumps(verify, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
