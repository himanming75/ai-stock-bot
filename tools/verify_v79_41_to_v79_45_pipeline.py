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
    output=root/"release/v79_45/output"
    cert_path=output/"historical_dataset_version_certificate_v79_45.json"
    verify_path=output/"historical_dataset_version_verify_v79_45.json"
    manifest_path=output/"dataset_version_manifest_v79_44.json"
    registry_path=output/"dataset_version_registry.json"
    for path in (cert_path,verify_path,manifest_path,registry_path):
        if not path.is_file(): raise SystemExit(f"VERIFY FAIL: missing {path}")
    cert=json.loads(cert_path.read_text(encoding="utf-8"))
    verify=json.loads(verify_path.read_text(encoding="utf-8"))
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    registry=json.loads(registry_path.read_text(encoding="utf-8"))
    unsigned=dict(cert); expected=unsigned.pop("certificate_sha256",None)
    checks={
        "certificate_status_pass":cert.get("status")=="PASS",
        "certificate_hash_valid":expected==digest(unsigned),
        "verify_status_pass":verify.get("status")=="PASS",
        "verify_flag_true":verify.get("verified") is True,
        "manifest_stage_v79_44":manifest.get("stage")=="V79.44",
        "immutable_version":manifest.get("immutable_version") is True,
        "deterministic_version_id":manifest.get("deterministic_version_id") is True,
        "registry_active_version_matches":(
            registry.get("active_version_id")
            ==cert.get("version_summary",{}).get("version_id")
        ),
        "network_requests_zero":cert.get("network_requests_executed")==0,
        "credentials_unused":cert.get("credentials_used")==0,
        "trading_client_not_created":cert.get("trading_client_created") is False,
        "actual_orders_zero":cert.get("actual_orders_submitted")==0,
        "live_trading_not_authorized":cert.get("live_trading_authorized") is False,
    }
    failed=[name for name,passed in checks.items() if not passed]
    print(json.dumps({
        "stage_range":"V79.41-V79.45",
        "status":"PASS" if not failed else "FAIL",
        "checks":checks,"failed_checks":failed,
        "next_phase":cert.get("next_phase"),
    },indent=2,sort_keys=True))
    return 0 if not failed else 1

if __name__=="__main__": raise SystemExit(main())
