from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v84_20/output"
 cp=o/"live_enablement_certificate_v84_20.json";vp=o/"live_enablement_verify_v84_20.json";mp=o/"live_enablement_manifest_v84_18.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("live_enablement_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v84_18":m.get("stage")=="V84.18","capabilities_positive":s.get("capability_count",0)>0,
 "write_capabilities_zero":s.get("write_capability_count")==0,"network_capabilities_zero":s.get("network_capability_count")==0,
 "credential_capabilities_zero":s.get("credential_capability_count")==0,"approval_threshold_met":s.get("approval_threshold_met") is True,
 "kill_switch_armed":s.get("kill_switch_state")=="ARMED","emergency_stop_ready":s.get("emergency_stop_state")=="READY",
 "session_pass":s.get("session_status")=="PASS","receipt_ready":s.get("permission_receipt_status")=="FOUNDATION_READY",
 "audit_pass":s.get("audit_status")=="PASS","foundation_complete":c.get("live_enablement_foundation_complete") is True,
 "live_not_authorized":c.get("live_trading_authorized") is False,"actual_orders_zero":c.get("actual_orders_submitted")==0}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V84.01-V84.20","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
