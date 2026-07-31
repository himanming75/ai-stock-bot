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
    cert_path = root / "release/v79_10/output/alpaca_historical_data_certificate_v79_10.json"
    verify_path = root / "release/v79_10/output/alpaca_historical_data_verification_v79_10.json"
    errors = []
    for path, name in ((cert_path, "certificate_missing"), (verify_path, "verification_missing")):
        if not path.is_file():
            errors.append(name)
    if errors:
        print(json.dumps({"stage": "V79.10", "status": "FAIL", "errors": errors}, indent=2))
        return 1

    cert = json.loads(cert_path.read_text(encoding="utf-8"))
    verification = json.loads(verify_path.read_text(encoding="utf-8"))
    stored = cert.pop("certificate_sha256", None)
    calculated = hashlib.sha256(canonical_json(cert).encode("utf-8")).hexdigest()
    cert["certificate_sha256"] = stored
    checks = {
        "certificate_status_pass": cert.get("status") == "PASS",
        "certificate_hash_valid": stored == calculated,
        "verification_status_pass": verification.get("status") == "PASS",
        "verification_links_certificate": verification.get("certificate_sha256") == stored,
        "all_five_stages_completed": cert.get("stages_completed") == ["V79.06", "V79.07", "V79.08", "V79.09", "V79.10"],
        "alpaca_sdk_installed": cert.get("install_status", {}).get("alpaca_py_installed") is True,
        "historical_client_importable": cert.get("install_status", {}).get("stock_historical_client_importable") is True,
        "records_present": cert.get("record_count", 0) > 0,
        "network_calls_zero": cert.get("network_calls_made") == 0,
        "credentials_unused": cert.get("credentials_used") == 0,
        "broker_disconnected": cert.get("broker_connected") is False,
        "trading_client_not_created": cert.get("trading_client_created") is False,
        "actual_orders_zero": cert.get("actual_orders_submitted") == 0,
        "live_trading_not_authorized": cert.get("live_trading_authorized") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "stage": "V79.10",
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
