from pathlib import Path
import argparse, hashlib, json
def canonical(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repository-root",default="."); args=ap.parse_args()
    root=Path(args.repository_root).resolve()
    cp=root/"release/v79_15/output/authenticated_historical_gate_certificate_v79_15.json"
    vp=root/"release/v79_15/output/authenticated_historical_gate_verification_v79_15.json"
    if not cp.is_file() or not vp.is_file():
        print(json.dumps({"stage":"V79.15","status":"FAIL","error":"output_missing"},indent=2)); return 1
    cert=json.loads(cp.read_text()); ver=json.loads(vp.read_text())
    stored=cert.pop("certificate_sha256",None); calc=hashlib.sha256(canonical(cert).encode()).hexdigest(); cert["certificate_sha256"]=stored
    checks={
      "certificate_status_pass":cert.get("status")=="PASS",
      "certificate_hash_valid":stored==calc,
      "verification_status_pass":ver.get("status")=="PASS",
      "verification_links_certificate":ver.get("certificate_sha256")==stored,
      "all_five_stages_completed":cert.get("stages_completed")==["V79.11","V79.12","V79.13","V79.14","V79.15"],
      "network_requests_zero":cert.get("network_requests_executed")==0,
      "credentials_not_exposed":cert.get("credentials_exposed") is False,
      "broker_disconnected":cert.get("broker_connected") is False,
      "trading_client_not_created":cert.get("trading_client_created") is False,
      "actual_orders_zero":cert.get("actual_orders_submitted")==0,
      "live_trading_not_authorized":cert.get("live_trading_authorized") is False,
    }
    failed=[k for k,v in checks.items() if not v]
    print(json.dumps({"stage":"V79.15","status":"PASS" if not failed else "FAIL",
      "verified":not failed,"checks":checks,"failed_checks":failed,"next_phase":cert.get("next_phase")},indent=2,sort_keys=True))
    return 0 if not failed else 1
if __name__=="__main__": raise SystemExit(main())
