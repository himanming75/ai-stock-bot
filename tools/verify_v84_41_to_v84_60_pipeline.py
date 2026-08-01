from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v84_60/output"
 cp=o/"live_order_authorization_certificate_v84_60.json";vp=o/"live_order_authorization_verify_v84_60.json";mp=o/"live_order_authorization_manifest_v84_58.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("live_order_authorization_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v84_58":m.get("stage")=="V84.58","approval_count_valid":s.get("approval_count",0)>=s.get("required_approvals",999),
 "token_issued":s.get("token_issued") is True,"token_validation_pass":s.get("token_validation_status")=="PASS",
 "bad_validation_fail":s.get("bad_token_validation_status")=="FAIL","receipt_ready":s.get("receipt_status")=="AUTHORIZATION_READY",
 "single_use_consumed":s.get("single_use_consumed") is True,"revocation_supported":s.get("revocation_supported") is True,
 "expiration_supported":s.get("expiration_supported") is True,"duplicate_detected":s.get("duplicate_detected") is True,
 "replay_detected":s.get("replay_detected") is True,"submit_capabilities_zero":s.get("submit_capability_count")==0,
 "network_capabilities_zero":s.get("network_capability_count")==0,"audit_pass":s.get("audit_status")=="PASS",
 "foundation_complete":c.get("live_order_authorization_foundation_complete") is True,
 "live_not_authorized":c.get("live_trading_authorized") is False,"actual_orders_zero":c.get("actual_orders_submitted")==0}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V84.41-V84.60","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
