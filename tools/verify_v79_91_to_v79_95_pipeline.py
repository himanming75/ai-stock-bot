from pathlib import Path
import argparse, hashlib, json

def digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()).hexdigest()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    output = Path(args.repository_root).resolve() / "release/v79_95/output"
    certificate_path = output / "historical_walk_forward_validation_certificate_v79_95.json"
    verify_path = output / "historical_walk_forward_validation_verify_v79_95.json"
    manifest_path = output / "historical_walk_forward_manifest_v79_94.json"
    for path in (certificate_path, verify_path, manifest_path):
        if not path.is_file():
            raise SystemExit(f"VERIFY FAIL: missing {path}")
    certificate = json.loads(certificate_path.read_text())
    verify = json.loads(verify_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    unsigned = dict(certificate)
    expected = unsigned.pop("certificate_sha256", None)
    summary = certificate.get("walk_forward_summary", {})
    checks = {
        "certificate_status_pass": certificate.get("status") == "PASS",
        "certificate_hash_valid": expected == digest(unsigned),
        "verify_flag_true": verify.get("verified") is True,
        "manifest_stage_v79_94": manifest.get("stage") == "V79.94",
        "minimum_fold_count_met": summary.get("fold_count", 0) >= 2,
        "leakage_zero": summary.get("leakage_count") == 0,
        "aggregate_status_pass": summary.get("status") == "PASS",
        "actual_orders_zero": certificate.get("actual_orders_submitted") == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    print(json.dumps({
        "stage_range": "V79.91-V79.95",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": certificate.get("next_phase"),
    }, indent=2, sort_keys=True))
    return 0 if not failed else 1

if __name__ == "__main__":
    raise SystemExit(main())
