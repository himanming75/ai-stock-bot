from __future__ import annotations
import tempfile,unittest,sys,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.paper_runtime_pipeline_v77_16_20 import *
class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
  self.cert=self.r/"v77_15.json"
  write_json(self.cert,{"certificate_id":"RECOVERY-RELEASE-V77.15","status":"PASS","certificate_sha256":"abc"})
 def tearDown(self):self.t.cleanup()
 def chain(self):
  o16=self.r/"o16";s16=build_session_orchestrator(self.cert,o16,session_id="TEST")
  session=o16/"paper_runtime_session_v77_16.json"
  o17=self.r/"o17";s17=build_state_ledger(session,o17)
  ledger=o17/"runtime_session_state_ledger_v77_17.json"
  o18=self.r/"o18";s18=recover_session(session,ledger,o18)
  recovery=o18/"automatic_restart_recovery_v77_18.json"
  o19=self.r/"o19";s19=run_stability(recovery,o19,cycles=100)
  o20=self.r/"o20";s20=issue_runtime_certificate(
   o16/"paper_runtime_session_verification_v77_16.json",
   o17/"runtime_session_state_ledger_verification_v77_17.json",
   o18/"automatic_restart_recovery_verification_v77_18.json",
   o19/"extended_paper_runtime_stability_verification_v77_19.json",o20)
  return s16,s17,s18,s19,s20
 def test_full_chain(self):self.assertTrue(all(x.status=="PASS" for x in self.chain()))
 def test_invalid_release_certificate(self):
  write_json(self.cert,{"certificate_id":"BAD","status":"PASS"})
  with self.assertRaises(PaperRuntimeError):build_session_orchestrator(self.cert,self.r/"x")
 def test_ledger_tamper_detection(self):
  o16=self.r/"o16";build_session_orchestrator(self.cert,o16,session_id="TEST")
  session=o16/"paper_runtime_session_v77_16.json";o17=self.r/"o17";build_state_ledger(session,o17)
  ledger_path=o17/"runtime_session_state_ledger_v77_17.json";ledger=load_json(ledger_path)
  ledger["events"][1]["payload"]["network_allowed"]=True;write_json(ledger_path,ledger)
  self.assertEqual(recover_session(session,ledger_path,self.r/"o18").status,"FAIL")
 def test_stability_minimum(self):
  self.chain()
  recovery=self.r/"o18/automatic_restart_recovery_v77_18.json"
  with self.assertRaises(PaperRuntimeError):run_stability(recovery,self.r/"small",cycles=99)
 def test_deterministic_digest(self):self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
