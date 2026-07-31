from pathlib import Path
import argparse, hashlib, json
def canonical(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def sha(data): return hashlib.sha256(data).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repository-root",default="."); args=ap.parse_args()
    root=Path(args.repository_root).resolve()
    cp=root/"release/v79_25/output/historical_ingestion_certificate_v79_25.json"
    vp=root/"release/v79_25/output/historical_ingestion_verification_v79_25.json"
    if not cp.is_file() or not vp.is_file():
        print(json.dumps({"stage":"V79.25","status":"FAIL","error":"output_missing"},indent=2)); return 1
    cert=json.loads(cp.read_text()); ver=json.loads(vp.read_text())
    stored=cert.pop("certificate_sha256",None); calc=sha(canonical(cert).encode()); cert["certificate_sha256"]=stored
    manifest=cert["dataset_manifest"]
    dataset_dir=root/"release/v79_25/output/dataset"
    file_checks={}
    for name,info in manifest["files"].items():
        path=dataset_dir/info["relative_path"]
        file_checks[f"{name}_present"]=path.is_file()
        file_checks[f"{name}_hash_valid"]=path.is_file() and sha(path.read_bytes())==info["sha256"]
        file_checks[f"{name}_size_valid"]=path.is_file() and len(path.read_bytes())==info["byte_size"]
    checks={
      "certificate_status_pass":cert.get("status")=="PASS",
      "certificate_hash_valid":stored==calc,
      "verification_status_pass":ver.get("status")=="PASS",
      "verification_links_certificate":ver.get("certificate_sha256")==stored,
      "all_five_stages_completed":cert.get("stages_completed")==["V79.21","V79.22","V79.23","V79.24","V79.25"],
      "stored_rows_present":cert.get("ingestion_summary",{}).get("stored_row_count",0)>0,
      "all_symbols_present":cert.get("ingestion_summary",{}).get("symbols")==["AAPL","MSFT","SPY"],
      "network_requests_zero":cert.get("network_requests_executed")==0,
      "credentials_unused":cert.get("credentials_used")==0,
      "trading_client_not_created":cert.get("trading_client_created") is False,
      "actual_orders_zero":cert.get("actual_orders_submitted")==0,
      "live_trading_not_authorized":cert.get("live_trading_authorized") is False,
      **file_checks,
    }
    failed=[k for k,v in checks.items() if not v]
    print(json.dumps({"stage":"V79.25","status":"PASS" if not failed else "FAIL",
      "verified":not failed,"checks":checks,"failed_checks":failed,
      "next_phase":cert.get("next_phase")},indent=2,sort_keys=True))
    return 0 if not failed else 1
if __name__=="__main__": raise SystemExit(main())
