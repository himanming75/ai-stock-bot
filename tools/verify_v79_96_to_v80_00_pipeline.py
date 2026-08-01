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
    output = Path(args.repository_root).resolve() / "release/v80_00/output"
    certificate_path = output / "historical_backtest_completion_certificate_v79_99.json"
    verify_path = output / "historical_backtest_completion_verify_v80_00.json"
    manifest_path = output / "historical_backtest_completion_manifest_v79_98.json"
    report_path = output / "historical_backtest_engine_completion_report_v80_00.json"
    for path in (certificate_path, verify_path, manifest_path, report_path):
        if not path.is_file():
            raise SystemExit(f"VERIFY FAIL: missing {path}")
    certificate = json.loads(certificate_path.read_text())
    verify = json.loads(verify_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    report = json.loads(report_path.read_text())
    unsigned = dict(certificate)
    expected = unsigned.pop("certificate_sha256", None)
    summary = certificate.get("completion_summary", {})
    checks = {
        "certificate_status_pass": certificate.get("status") == "PASS",
        "certificate_hash_valid": expected == digest(unsigned),
        "verify_flag_true": verify.get("verified") is True,
        "manifest_stage_v79_98": manifest.get("stage") == "V79.98",
        "report_stage_v80_00": report.get("stage") == "V80.00",
        "seven_certificates_verified": summary.get("certificate_count") == 7,
        "historical_engine_complete": summary.get("historical_engine_complete") is True,
        "risk_violations_zero": summary.get("risk_violation_count") == 0,
        "walk_forward_leakage_zero": summary.get("walk_forward_leakage_count") == 0,
        "actual_orders_zero": certificate.get("actual_orders_submitted") == 0,
        "paper_trading_not_authorized": certificate.get("paper_trading_authorized") is False,
        "live_trading_not_authorized": certificate.get("live_trading_authorized") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    print(json.dumps({
        "stage_range": "V79.96-V80.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": certificate.get("next_phase"),
    }, indent=2, sort_keys=True))
    return 0 if not failed else 1

if __name__ == "__main__":
    raise SystemExit(main())
