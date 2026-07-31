from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from broker.recovery_audit_certificate_v77_10 import RecoveryAuditCertificateBuilder
from tools.recovery_audit_certificate_v77_10 import verify,summary
from tools.verify_recovery_audit_certificate_v77_10 import verify_output
class Tests(unittest.TestCase):
 def stages(self):return [{"version":f"V77.{i}","status":"PASS","verification_sha256":str(i)*64,
 "failed_gate_count":0,"environment":"offline","network_allowed":False,
 "broker_connected":False,"actual_orders_submitted":0,"live_trading_authorized":False} for i in range(5,10)]
 def test_certificate_builds(self):
  b=RecoveryAuditCertificateBuilder();c=b.build(certificate_id="X",stages=self.stages(),
  safety_policy={"a":True},state_continuity={"b":True});self.assertTrue(b.verify(c))
 def test_stage_order_required(self):
  with self.assertRaises(Exception):RecoveryAuditCertificateBuilder().build(certificate_id="X",
  stages=list(reversed(self.stages())),safety_policy={"a":True},state_continuity={"b":True})
 def test_certificate_hash_changes(self):
  b=RecoveryAuditCertificateBuilder();c1=b.build(certificate_id="X",stages=self.stages(),safety_policy={"a":True},state_continuity={"b":True})
  c2=b.build(certificate_id="Y",stages=self.stages(),safety_policy={"a":True},state_continuity={"b":True});self.assertNotEqual(c1.certificate_sha256,c2.certificate_sha256)
 def test_outputs(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);cfg={"expected_framework_commit_sha":"a","expected_anchors":{}}
   vals={"V77.5":{"status":"PASS","broker_state_checkpoint_sha256":"p","sample_state_sha256":"s","verification_sha256":"5"},
   "V77.6":{"status":"PASS","restart_recovery_replay_sha256":"r","replayed_state_sha256":"s","verification_sha256":"6"},
   "V77.7":{"status":"PASS","recovery_continuation_safety_sha256":"x","continuation_report":{"continued_checkpoint_sha256":"c"},"verification_sha256":"7"},
   "V77.8":{"status":"PASS","multi_order_continuation_stress_sha256":"m","stress_report":{"stressed_state_sha256":"z"},"verification_sha256":"8"},
   "V77.9":{"status":"PASS","failure_injection_recovery_sha256":"f","failure_report":{"recovered_state_sha256":"s"},"verification_sha256":"9"}}
   files={"V77.5":"release/v77_5/output/broker_state_checkpoint_verification_v77_5.json",
   "V77.6":"release/v77_6/output/restart_recovery_replay_verification_v77_6.json",
   "V77.7":"release/v77_7/output/recovery_continuation_safety_verification_v77_7.json",
   "V77.8":"release/v77_8/output/multi_order_continuation_stress_verification_v77_8.json",
   "V77.9":"release/v77_9/output/failure_injection_recovery_verification_v77_9.json"}
   for v,d in vals.items():
    d.update({"verification_result":{"failed_gate_count":0},"environment":"offline","network_allowed":False,
    "broker_connected":False,"actual_orders_submitted":0,"live_trading_authorized":False})
    p=root/files[v];p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d))
   cfg["expected_anchors"]={"v77_5_checkpoint":"p","v77_5_state":"s","v77_5_verify":"5","v77_6_recovery":"r","v77_6_state":"s","v77_6_verify":"6","v77_7_safety":"x","v77_7_checkpoint":"c","v77_7_verify":"7","v77_8_stress":"m","v77_8_state":"z","v77_8_verify":"8","v77_9_failure":"f","v77_9_recovered":"s","v77_9_verify":"9"}
   with patch("tools.recovery_audit_certificate_v77_10.git",side_effect=["e"*40,"e"*40,"main"]),patch("tools.recovery_audit_certificate_v77_10.anc",return_value=True):r=verify(root,cfg)
   o=root/"release/v77_10/output";o.mkdir(parents=True)
   (o/"recovery_audit_certificate_v77_10.json").write_text(json.dumps(r["certificate"],indent=2,sort_keys=True))
   (o/"recovery_audit_certificate_verification_v77_10.json").write_text(json.dumps(r,indent=2,sort_keys=True))
   (o/"recovery_audit_certificate_summary_v77_10.json").write_text(json.dumps(summary(r),indent=2,sort_keys=True))
   self.assertTrue(verify_output(o)["verified"])
if __name__=="__main__":unittest.main()
