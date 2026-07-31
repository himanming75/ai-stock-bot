from pathlib import Path
import argparse
import hashlib
import json


def sha256_json(value):
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()
    output = root / "release/v79_35/output"
    cert_path = output / "historical_gap_fill_certificate_v79_35.json"
    verify_path = output / "historical_gap_fill_verify_v79_35.json"
    manifest_path = output / "gap_fill/alpaca_historical_bars.gap_fill_manifest.json"

    for path in (cert_path, verify_path, manifest_path):
        if not path.is_file():
            raise SystemExit(f"VERIFY FAIL: missing {path}")

    cert = json.loads(cert_path.read_text(encoding="utf-8"))
    verify = json.loads(verify_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    unsigned_cert = dict(cert)
    cert_hash = unsigned_cert.pop("certificate_sha256", None)
    checks = {
        "certificate_status_pass": cert.get("status") == "PASS",
        "certificate_hash_valid": cert_hash == sha256_json(unsigned_cert),
        "verify_status_pass": verify.get("status") == "PASS",
        "verify_flag_true": verify.get("verified") is True,
        "manifest_stage_v79_34": manifest.get("stage") == "V79.34",
        "remaining_gap_tasks_zero": (
            cert.get("gap_fill_summary", {}).get("remaining_gap_task_count") == 0
        ),
        "network_requests_zero": cert.get("network_requests_executed") == 0,
        "credentials_unused": cert.get("credentials_used") == 0,
        "trading_client_not_created": cert.get("trading_client_created") is False,
        "actual_orders_zero": cert.get("actual_orders_submitted") == 0,
        "live_trading_not_authorized": cert.get("live_trading_authorized") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "stage_range": "V79.31-V79.35",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": cert.get("next_phase"),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
