from __future__ import annotations
import argparse,hashlib,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.recovery_audit_certificate_v77_10 import RecoveryAuditCertificateBuilder
NEXT="V77_11_RECOVERY_RELEASE_MANIFEST"
def canon(v:Any)->str:return json.dumps(v,sort_keys=True,separators=(",",":"))
def digest(v:Any)->str:return hashlib.sha256(canon(v).encode()).hexdigest()
def load(p:Path):return json.loads(p.read_text(encoding="utf-8"))
def git(r,*a):
 p=subprocess.run(["git",*a],cwd=r,capture_output=True,text=True)
 if p.returncode:raise ValueError(p.stderr.strip())
 return p.stdout.strip()
def anc(r,s):return subprocess.run(["git","merge-base","--is-ancestor",s,"HEAD"],cwd=r).returncode==0
def verify(root:Path,cfg:dict):
 paths={
 "V77.5":root/"release/v77_5/output/broker_state_checkpoint_verification_v77_5.json",
 "V77.6":root/"release/v77_6/output/restart_recovery_replay_verification_v77_6.json",
 "V77.7":root/"release/v77_7/output/recovery_continuation_safety_verification_v77_7.json",
 "V77.8":root/"release/v77_8/output/multi_order_continuation_stress_verification_v77_8.json",
 "V77.9":root/"release/v77_9/output/failure_injection_recovery_verification_v77_9.json"}
 docs={k:load(v) for k,v in paths.items()}
 head=git(root,"rev-parse","HEAD");origin=git(root,"rev-parse","origin/main");branch=git(root,"rev-parse","--abbrev-ref","HEAD")
 gates=[]
 def g(n,p):gates.append({"gate_id":n,"status":"PASS" if p else "FAIL"})
 g("GIT_HEAD_MATCHES_ORIGIN",head==origin);g("BRANCH_MAIN",branch=="main");g("BASE_ANCESTOR",anc(root,cfg["expected_framework_commit_sha"]))
 for v,d in docs.items():
  g(f"{v}_STATUS_PASS",d.get("status")=="PASS")
  g(f"{v}_FAILED_GATES_ZERO",d.get("verification_result",{}).get("failed_gate_count")==0)
  g(f"{v}_OFFLINE",d.get("environment")=="offline")
  g(f"{v}_NETWORK_DISABLED",d.get("network_allowed") is False)
  g(f"{v}_BROKER_DISCONNECTED",d.get("broker_connected") is False)
  g(f"{v}_ACTUAL_ORDERS_ZERO",d.get("actual_orders_submitted")==0)
  g(f"{v}_LIVE_UNAUTHORIZED",d.get("live_trading_authorized") is False)
 a=cfg["expected_anchors"]
 def first(*values):
  return next((value for value in values if value not in (None, "")), None)
 actual={
 "v77_5_checkpoint":first(
  docs["V77.5"].get("broker_state_checkpoint_sha256"),
  docs["V77.5"].get("checkpoint_sha256"),
  docs["V77.5"].get("checkpoint",{}).get("state_sha256")),
 "v77_5_state":first(
  docs["V77.5"].get("sample_state_sha256"),
  docs["V77.5"].get("state_sha256"),
  docs["V77.5"].get("checkpoint",{}).get("state_sha256"),
  docs["V77.5"].get("sample_checkpoint",{}).get("state_sha256")),
 "v77_5_verify":docs["V77.5"].get("verification_sha256"),
 "v77_6_recovery":docs["V77.6"].get("restart_recovery_replay_sha256"),
 "v77_6_state":first(
  docs["V77.6"].get("replayed_state_sha256"),
  docs["V77.6"].get("replay_report",{}).get("replayed_state_sha256"),
  docs["V77.6"].get("recovery_report",{}).get("replayed_state_sha256")),
 "v77_6_verify":docs["V77.6"].get("verification_sha256"),
 "v77_7_safety":docs["V77.7"].get("recovery_continuation_safety_sha256"),
 "v77_7_checkpoint":first(
  docs["V77.7"].get("continued_checkpoint_sha256"),
  docs["V77.7"].get("continuation_report",{}).get("continued_checkpoint_sha256"),
  docs["V77.7"].get("recovery_continuation_report",{}).get("continued_checkpoint_sha256")),
 "v77_7_verify":docs["V77.7"].get("verification_sha256"),
 "v77_8_stress":docs["V77.8"].get("multi_order_continuation_stress_sha256"),
 "v77_8_state":first(
  docs["V77.8"].get("stressed_state_sha256"),
  docs["V77.8"].get("stress_report",{}).get("stressed_state_sha256"),
  docs["V77.8"].get("multi_order_stress_report",{}).get("stressed_state_sha256")),
 "v77_8_verify":docs["V77.8"].get("verification_sha256"),
 "v77_9_failure":docs["V77.9"].get("failure_injection_recovery_sha256"),
 "v77_9_recovered":first(
  docs["V77.9"].get("recovered_state_sha256"),
  docs["V77.9"].get("failure_report",{}).get("recovered_state_sha256"),
  docs["V77.9"].get("failure_injection_report",{}).get("recovered_state_sha256")),
 "v77_9_verify":docs["V77.9"].get("verification_sha256")}
 for k,v in a.items():g("ANCHOR_"+k.upper(),actual.get(k)==v)
 state={
 "v77_5_equals_v77_6":actual["v77_5_state"]==actual["v77_6_state"],
 "v77_5_equals_v77_9_recovered":actual["v77_5_state"]==actual["v77_9_recovered"],
 "v77_8_stress_differs_from_base":actual["v77_8_state"]!=actual["v77_5_state"],
 "v77_7_continuation_differs_from_base":actual["v77_7_checkpoint"]!=actual["v77_5_state"]}
 for k,v in state.items():g("STATE_"+k.upper(),v)
 stages=[]
 for v,d in docs.items():
  stages.append({"version":v,"status":d.get("status"),"verification_sha256":d.get("verification_sha256"),
  "failed_gate_count":d.get("verification_result",{}).get("failed_gate_count"),
  "environment":d.get("environment"),"network_allowed":d.get("network_allowed"),
  "broker_connected":d.get("broker_connected"),"actual_orders_submitted":d.get("actual_orders_submitted"),
  "live_trading_authorized":d.get("live_trading_authorized")})
 safety={"all_offline":all(x["environment"]=="offline" for x in stages),
 "network_disabled":all(x["network_allowed"] is False for x in stages),
 "broker_disconnected":all(x["broker_connected"] is False for x in stages),
 "actual_orders_zero":all(x["actual_orders_submitted"]==0 for x in stages),
 "live_trading_unauthorized":all(x["live_trading_authorized"] is False for x in stages)}
 builder=RecoveryAuditCertificateBuilder()
 false_state=[name for name,value in state.items() if not value]
 if false_state:
  raise ValueError(
   "state continuity failed: "
   + ", ".join(false_state)
   + " | extracted="
   + json.dumps({
      "v77_5_state":actual["v77_5_state"],
      "v77_6_state":actual["v77_6_state"],
      "v77_7_checkpoint":actual["v77_7_checkpoint"],
      "v77_8_state":actual["v77_8_state"],
      "v77_9_recovered":actual["v77_9_recovered"],
     }, sort_keys=True)
  )
 cert=builder.build(certificate_id="RECOVERY-AUDIT-V77.10",stages=stages,safety_policy=safety,state_continuity=state)
 g("CERTIFICATE_VALID",builder.verify(cert))
 failed=[x["gate_id"] for x in gates if x["status"]=="FAIL"];status="PASS" if not failed else "FAIL"
 result={"schema_version":"v77.10.recovery_audit_certificate_verification.1","version":"77.10",
 "issued_at_utc":datetime.now(timezone.utc).isoformat(),"status":status,
 "decision":"recovery_audit_certificate_issued" if status=="PASS" else "recovery_audit_certificate_rejected",
 "repository":{"framework_commit_sha":head,"origin_main_sha":origin,"branch":branch},
 "source_anchors":actual,"certificate":cert.as_dict(),
 "verification_result":{"gate_count":len(gates),"passed_gate_count":len(gates)-len(failed),
 "failed_gate_count":len(failed),"failed_gate_ids":failed,"gates":gates},
 "environment":"offline","network_allowed":False,"broker_connected":False,
 "actual_orders_submitted":0,"live_trading_authorized":False,
 "next_phase":NEXT if status=="PASS" else "REPAIR_V77_10_RECOVERY_AUDIT_CERTIFICATE"}
 result["verification_sha256"]=digest({k:v for k,v in result.items() if k not in {"verification_sha256","issued_at_utc"}})
 return result
def summary(r):
 vr=r["verification_result"];c=r["certificate"]
 return {"status":r["status"],"decision":r["decision"],"framework_commit_sha":r["repository"]["framework_commit_sha"],
 "recovery_audit_certificate_sha256":c["certificate_sha256"],"verification_sha256":r["verification_sha256"],
 "stage_count":c["stage_count"],"chain_start_version":c["chain_start_version"],
 "chain_end_version":c["chain_end_version"],"gate_count":vr["gate_count"],
 "passed_gate_count":vr["passed_gate_count"],"failed_gate_count":vr["failed_gate_count"],
 "failed_gate_ids":vr["failed_gate_ids"],"state_continuity":c["state_continuity"],
 "safety_policy":c["safety_policy"],"environment":r["environment"],
 "network_allowed":r["network_allowed"],"broker_connected":r["broker_connected"],
 "actual_orders_submitted":r["actual_orders_submitted"],"live_trading_authorized":r["live_trading_authorized"],
 "next_phase":r["next_phase"]}
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",required=True);p.add_argument("--config",required=True);p.add_argument("--output-dir",required=True);a=p.parse_args()
 r=verify(Path(a.repository_root).resolve(),load(Path(a.config)));o=Path(a.output_dir);o.mkdir(parents=True,exist_ok=True)
 (o/"recovery_audit_certificate_v77_10.json").write_text(json.dumps(r["certificate"],indent=2,sort_keys=True)+"\n")
 (o/"recovery_audit_certificate_verification_v77_10.json").write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
 (o/"recovery_audit_certificate_summary_v77_10.json").write_text(json.dumps(summary(r),indent=2,sort_keys=True)+"\n")
 print(json.dumps(summary(r),indent=2));return 0 if r["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
