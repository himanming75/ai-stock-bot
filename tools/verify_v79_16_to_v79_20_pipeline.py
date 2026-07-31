from pathlib import Path
import argparse, hashlib, json
def canonical(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repository-root",default="."); args=ap.parse_args()
    root=Path(args.repository_root).resolve()
    cp=root/"release/v79_20/output/historical_network_smoke_certificate_v79_20.json"
    vp=root/"release/v79_20/output/historical_network_smoke_verification_v79_20.json"
    if not cp.is_file() or not vp.is_file():
        print(json.dumps({"stage":"V79.20","status":"FAIL","error":"output_missing"},indent=2)); return 1
    cert=json.loads(cp.read_text()); ver=json.loads(vp.read_text())
    stored=cert.pop("certificate_sha256",None)
    calc=hashlib.sha256(canonical(cert).encode()).hexdigest()
    cert["certificate_sha256"]=stored
    checks={
      "certificate_status_pass":cert.get("status")=="PASS",
      "certificate_hash_valid":stored==calc,
      "verification_status_pass":ver.get("status")=="PASS",
      "verification_links_certificate":ver.get("certificate_sha256")==stored,
      "all_five_stages_completed":cert.get("stages_completed")==["V79.16","V79.17","V79.18","V79.19","V79.20"],
      "mode_is_safe_or_pass":cert.get("network_smoke_mode") in {"SKIPPED_SAFE","PASS"},
      "credentials_not_exposed":cert.get("credentials_exposed") is False,
      "broker_disconnected":cert.get("broker_connected") is False,
      "trading_client_not_created":cert.get("trading_client_created") is False,
      "actual_orders_zero":cert.get("actual_orders_submitted")==0,
      "live_trading_not_authorized":cert.get("live_trading_authorized") is False,
    }
    failed=[k for k,v in checks.items() if not v]
    print(json.dumps({"stage":"V79.20","status":"PASS" if not failed else "FAIL",
      "verified":not failed,"checks":checks,"failed_checks":failed,
      "next_phase":cert.get("next_phase")},indent=2,sort_keys=True))
    return 0 if not failed else 1
if __name__=="__main__": raise SystemExit(main())
