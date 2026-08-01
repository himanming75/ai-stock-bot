from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v85_20/output"
 cp=o/"paper_network_foundation_certificate_v85_20.json";vp=o/"paper_network_foundation_verify_v85_20.json";mp=o/"paper_network_foundation_manifest_v85_19.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("paper_network_foundation_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v85_19":m.get("stage")=="V85.19","read_capabilities_positive":s.get("read_capability_count",0)>0,
 "write_capabilities_zero":s.get("write_capability_count")==0,"endpoint_count_six":s.get("endpoint_count")==6,
 "write_endpoints_zero":s.get("write_endpoint_count")==0,"schema_count_six":s.get("schema_count")==6,
 "network_opt_in_default_false":s.get("network_opt_in_default") is False,"actual_network_zero":s.get("actual_network_requests")==0,
 "audit_pass":s.get("audit_status")=="PASS","foundation_complete":c.get("paper_network_foundation_complete") is True,
 "network_not_authorized":c.get("paper_network_connection_authorized") is False,
 "orders_zero":c.get("actual_orders_submitted")==0}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V85.01-V85.20","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
