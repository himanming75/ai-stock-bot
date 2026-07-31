from pathlib import Path
import argparse
import hashlib
import json

def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()
    cert_path = root / "release" / "v79_05" / "output" / "alpaca_market_data_foundation_certificate_v79_05.json"
    verify_path = root / "release" / "v79_05" / "output" / "alpaca_market_data_foundation_verification_v79_05.json"

    errors = []
    if not cert_path.is_file():
        errors.append("certificate_missing")
    if not verify_path.is_file():
        errors.append("verification_missing")
    if errors:
        print(json.dumps({"stage": "V79.05", "status": "FAIL", "errors": errors}, indent=2))
        return 1

    cert = json.loads(cert_path.read_text(encoding="utf-8"))
    verification = json.loads(verify_path.read_text(encoding="utf-8"))
    stored_hash = cert.pop("certificate_sha256", None)
    calculated_hash = hashlib.sha256(canonical_json(cert).encode("utf-8")).hexdigest()
    cert["certificate_sha256"] = stored_hash

    checks = {
        "certificate_status_pass": cert.get("status") == "PASS",
        "certificate_hash_valid": stored_hash == calculated_hash,
        "verification_status_pass": verification.get("status") == "PASS",
        "verification_links_certificate": verification.get("certificate_sha256") == stored_hash,
        "all_five_stages_completed": cert.get("stages_completed") == ["V79.01", "V79.02", "V79.03", "V79.04", "V79.05"],
        "network_calls_zero": cert.get("network_calls_made") == 0,
        "broker_disconnected": cert.get("broker_connected") is False,
        "actual_orders_zero": cert.get("actual_orders_submitted") == 0,
        "real_credentials_unused": cert.get("real_credentials_used") is False,
        "live_trading_not_authorized": cert.get("live_trading_authorized") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "stage": "V79.05",
        "status": "PASS" if not failed else "FAIL",
        "verified": not failed,
        "checks": checks,
        "failed_checks": failed,
        "next_phase": cert.get("next_phase"),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not failed else 1

if __name__ == "__main__":
    raise SystemExit(main())
