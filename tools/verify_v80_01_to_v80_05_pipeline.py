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
    output = Path(args.repository_root).resolve() / "release/v80_05/output"
    certificate_path = output / "paper_trading_readiness_certificate_v80_05.json"
    verify_path = output / "paper_trading_readiness_verify_v80_05.json"
    manifest_path = output / "paper_trading_readiness_manifest_v80_04.json"
    for path in (certificate_path, verify_path, manifest_path):
        if not path.is_file():
            raise SystemExit(f"VERIFY FAIL: missing {path}")
    certificate = json.loads(certificate_path.read_text())
    verify = json.loads(verify_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    unsigned = dict(certificate)
    expected = unsigned.pop("certificate_sha256", None)
    summary = certificate.get("readiness_summary", {})
    checks = {
        "certificate_status_pass": certificate.get("status") == "PASS",
        "certificate_hash_valid": expected == digest(unsigned),
        "verify_flag_true": verify.get("verified") is True,
        "manifest_stage_v80_04": manifest.get("stage") == "V80.04",
        "readiness_level_foundation": summary.get("readiness_level") == "FOUNDATION_READY_NO_BROKER_CONNECTION",
        "intent_receipts_positive": summary.get("intent_receipt_count", 0) > 0,
        "forbidden_capabilities_zero": summary.get("forbidden_capability_count") == 0,
        "network_requests_zero": certificate.get("network_requests_executed") == 0,
        "credentials_unused": certificate.get("credentials_used") == 0,
        "trading_client_not_created": certificate.get("trading_client_created") is False,
        "actual_orders_zero": certificate.get("actual_orders_submitted") == 0,
        "paper_trading_not_authorized": certificate.get("paper_trading_authorized") is False,
        "live_trading_not_authorized": certificate.get("live_trading_authorized") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    print(json.dumps({
        "stage_range": "V80.01-V80.05",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": certificate.get("next_phase"),
    }, indent=2, sort_keys=True))
    return 0 if not failed else 1

if __name__ == "__main__":
    raise SystemExit(main())
