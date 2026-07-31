from pathlib import Path
import argparse, hashlib, json

def digest(value):
    return hashlib.sha256(json.dumps(
        value,sort_keys=True,separators=(",",":"),ensure_ascii=False
    ).encode()).hexdigest()

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--repository-root",default=".")
    args=parser.parse_args()
    root=Path(args.repository_root).resolve()
    output=root/"release/v79_50/output"
    cert_path=output/"historical_dataset_retention_certificate_v79_50.json"
    verify_path=output/"historical_dataset_retention_verify_v79_50.json"
    manifest_path=output/"dataset_retention_manifest_v79_49.json"
    ledger_path=output/"dataset_retention_execution_ledger.json"
    for path in (cert_path,verify_path,manifest_path,ledger_path):
        if not path.is_file(): raise SystemExit(f"VERIFY FAIL: missing {path}")
    cert=json.loads(cert_path.read_text(encoding="utf-8"))
    verify=json.loads(verify_path.read_text(encoding="utf-8"))
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    ledger=json.loads(ledger_path.read_text(encoding="utf-8"))
    unsigned=dict(cert); expected=unsigned.pop("certificate_sha256",None)
    checks={
        "certificate_status_pass":cert.get("status")=="PASS",
        "certificate_hash_valid":expected==digest(unsigned),
        "verify_status_pass":verify.get("status")=="PASS",
        "verify_flag_true":verify.get("verified") is True,
        "manifest_stage_v79_49":manifest.get("stage")=="V79.49",
        "active_version_preserved":cert.get("checks",{}).get("active_version_preserved") is True,
        "physical_deletes_zero":ledger.get("deleted_version_count")==0,
        "source_versions_preserved":ledger.get("source_versions_preserved") is True,
        "network_requests_zero":cert.get("network_requests_executed")==0,
        "credentials_unused":cert.get("credentials_used")==0,
        "trading_client_not_created":cert.get("trading_client_created") is False,
        "actual_orders_zero":cert.get("actual_orders_submitted")==0,
        "live_trading_not_authorized":cert.get("live_trading_authorized") is False,
    }
    failed=[name for name,passed in checks.items() if not passed]
    print(json.dumps({
        "stage_range":"V79.46-V79.50",
        "status":"PASS" if not failed else "FAIL",
        "checks":checks,"failed_checks":failed,
        "next_phase":cert.get("next_phase"),
    },indent=2,sort_keys=True))
    return 0 if not failed else 1

if __name__=="__main__": raise SystemExit(main())
