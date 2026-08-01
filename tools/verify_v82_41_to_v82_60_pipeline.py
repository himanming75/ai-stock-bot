from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v82_60/output"
 cp=o/"broker_connection_validation_certificate_v82_60.json";vp=o/"broker_connection_validation_verify_v82_60.json";mp=o/"broker_connection_validation_manifest_v82_58.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("broker_connection_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v82_58":m.get("stage")=="V82.58","endpoint_count_six":s.get("endpoint_count")==6,
 "write_endpoints_zero":s.get("write_endpoint_count")==0,"schema_count_six":s.get("schema_count")==6,
 "heartbeat_healthy":s.get("heartbeat_healthy") is True,"connection_health_pass":s.get("connection_health_status")=="PASS",
 "read_only_compatible":s.get("read_only_compatible") is True,"write_not_compatible":s.get("write_compatible") is False,
 "audit_pass":s.get("audit_status")=="PASS","validation_complete":c.get("broker_connection_validation_complete") is True,
 "actual_orders_zero":c.get("actual_orders_submitted")==0,"paper_not_authorized":c.get("paper_trading_authorized") is False,
 "live_not_authorized":c.get("live_trading_authorized") is False}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V82.41-V82.60","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
