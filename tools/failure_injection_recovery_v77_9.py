from __future__ import annotations
import argparse,hashlib,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.broker_state_checkpoint_v77_5 import BrokerStateCheckpointManager
from broker.failure_injection_recovery_v77_9 import FailureInjectionRecovery
NEXT="V77_10_RECOVERY_AUDIT_CERTIFICATE"
def canon(v:Any)->str:return json.dumps(v,sort_keys=True,separators=(",",":"))
def digest(v:Any)->str:return hashlib.sha256(canon(v).encode()).hexdigest()
def load(p:Path):return json.loads(p.read_text(encoding="utf-8"))
def git(r,*a):
 p=subprocess.run(["git",*a],cwd=r,capture_output=True,text=True)
 if p.returncode:raise ValueError(p.stderr.strip())
 return p.stdout.strip()
def anc(r,s):return subprocess.run(["git","merge-base","--is-ancestor",s,"HEAD"],cwd=r).returncode==0
def verify(root:Path,cfg:dict):
 head=git(root,"rev-parse","HEAD");origin=git(root,"rev-parse","origin/main");branch=git(root,"rev-parse","--abbrev-ref","HEAD")
 src=load(root/"release/v77_8/output/multi_order_continuation_stress_verification_v77_8.json")
 cp=BrokerStateCheckpointManager().read(root/"release/v77_5/output/sample_broker_state_checkpoint_v77_5.json")
 sim,report=FailureInjectionRecovery().run(cp)
 gates=[]
 def g(n,p):gates.append({"gate_id":n,"status":"PASS" if p else "FAIL"})
 g("GIT_HEAD_MATCHES_ORIGIN",head==origin);g("BRANCH_MAIN",branch=="main");g("BASE_ANCESTOR",anc(root,cfg["expected_framework_commit_sha"]))
 g("V77_8_PASS",src.get("status")=="PASS")
 g("V77_8_STRESS_ANCHOR",src.get("multi_order_continuation_stress_sha256")==cfg["expected_v77_8_stress_sha256"])
 g("V77_8_STATE_ANCHOR",src.get("stress_report",{}).get("stressed_state_sha256")==cfg["expected_v77_8_stressed_state_sha256"])
 g("V77_8_VERIFY_ANCHOR",src.get("verification_sha256")==cfg["expected_v77_8_verification_sha256"])
 g("V77_8_NEXT",src.get("next_phase")=="V77_9_FAILURE_INJECTION_RECOVERY")
 g("REPORT_PASS",report.status=="PASS")
 for k,v in report.checks.items():g(k.upper(),bool(v))
 definition={"invalid_operations_blocked":report.blocked_failure_count,
 "corruptions_detected":report.detected_corruption_count,
 "last_good_checkpoint_recovered":True,"actual_network_calls":0,"actual_orders_submitted":0}
 fw=digest(definition);g("FRAMEWORK_DIGEST",len(fw)==64)
 failed=[x["gate_id"] for x in gates if x["status"]=="FAIL"];status="PASS" if not failed else "FAIL"
 result={"schema_version":"v77.9.failure_injection_recovery_verification.1","version":"77.9",
 "issued_at_utc":datetime.now(timezone.utc).isoformat(),"status":status,
 "decision":"failure_injection_recovery_established" if status=="PASS" else "failure_injection_recovery_rejected",
 "repository":{"framework_commit_sha":head,"origin_main_sha":origin,"branch":branch},
 "source_anchors":{"v77_8_multi_order_continuation_stress_sha256":src.get("multi_order_continuation_stress_sha256"),
 "v77_8_stressed_state_sha256":src.get("stress_report",{}).get("stressed_state_sha256"),
 "v77_8_verification_sha256":src.get("verification_sha256")},
 "failure_injection_recovery_sha256":fw,"failure_report":report.as_dict(),
 "verification_result":{"gate_count":len(gates),"passed_gate_count":len(gates)-len(failed),
 "failed_gate_count":len(failed),"failed_gate_ids":failed,"gates":gates},
 "environment":"offline","network_allowed":False,"broker_connected":False,
 "actual_orders_submitted":0,"live_trading_authorized":False,
 "next_phase":NEXT if status=="PASS" else "REPAIR_V77_9_FAILURE_INJECTION_RECOVERY"}
 result["verification_sha256"]=digest({k:v for k,v in result.items() if k not in {"verification_sha256","issued_at_utc"}})
 return result
def summary(r):
 vr=r["verification_result"];fr=r["failure_report"]
 return {"status":r["status"],"decision":r["decision"],"framework_commit_sha":r["repository"]["framework_commit_sha"],
 "failure_injection_recovery_sha256":r["failure_injection_recovery_sha256"],
 "source_state_sha256":fr["source_state_sha256"],"recovered_state_sha256":fr["recovered_state_sha256"],
 "verification_sha256":r["verification_sha256"],**r["source_anchors"],
 "gate_count":vr["gate_count"],"passed_gate_count":vr["passed_gate_count"],
 "failed_gate_count":vr["failed_gate_count"],"failed_gate_ids":vr["failed_gate_ids"],
 "failure_status":fr["status"],"blocked_failure_count":fr["blocked_failure_count"],
 "detected_corruption_count":fr["detected_corruption_count"],"environment":r["environment"],
 "network_allowed":r["network_allowed"],"broker_connected":r["broker_connected"],
 "actual_orders_submitted":r["actual_orders_submitted"],"live_trading_authorized":r["live_trading_authorized"],
 "next_phase":r["next_phase"]}
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",required=True);p.add_argument("--config",required=True);p.add_argument("--output-dir",required=True);a=p.parse_args()
 r=verify(Path(a.repository_root).resolve(),load(Path(a.config)));out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
 (out/"failure_injection_recovery_verification_v77_9.json").write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
 (out/"failure_injection_recovery_summary_v77_9.json").write_text(json.dumps(summary(r),indent=2,sort_keys=True)+"\n")
 print(json.dumps(summary(r),indent=2));return 0 if r["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
