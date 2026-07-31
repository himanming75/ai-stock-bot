import tempfile,unittest
from pathlib import Path
from paper_session.paper_session_pipeline_v78_16_20 import *
class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
        self.cert=self.r/"cert.json";self.cfg=self.r/"cfg.json"
        write_json(self.cert,{"stage":"V78.15","status":"PASS","certification_scope":"OFFLINE_SESSION_MANAGER_DEVELOPMENT_ONLY",
          "champion_candidate":{"candidate_id":"abc"}})
        write_json(self.cfg,{"paper_session":{"session_id":"TEST","starting_cash":100000.0,
          "default_state":"CREATED","checkpoint_enabled":True}})
    def tearDown(self):self.t.cleanup()
    def chain(self):
        o16=self.r/"o16";a=build_session_manager_foundation(self.cert,self.cfg,o16)
        o17=self.r/"o17";b=run_session_lifecycle(o16/"paper_session_manager_foundation_v78_16.json",o17)
        o18=self.r/"o18";c=run_checkpoint_resume(o16/"paper_session_manager_foundation_v78_16.json",o18)
        o19=self.r/"o19";d=run_session_manager_safety_gate(
          o16/"paper_session_manager_foundation_v78_16.json",
          o17/"session_lifecycle_state_machine_v78_17.json",
          o18/"session_checkpoint_resume_v78_18.json",o19)
        o20=self.r/"o20";e=issue_session_manager_certificate(
          o16/"paper_session_manager_foundation_verification_v78_16.json",
          o17/"session_lifecycle_state_machine_verification_v78_17.json",
          o18/"session_checkpoint_resume_verification_v78_18.json",
          o19/"session_manager_safety_gate_verification_v78_19.json",
          o16/"paper_session_manager_foundation_v78_16.json",o20)
        return a,b,c,d,e
    def test_full_chain(self):self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))
    def test_valid_lifecycle(self):
        m=PaperSessionManager("x");m.start();m.pause();m.resume();m.stop();self.assertEqual(m.state,"STOPPED")
    def test_invalid_transition_blocked(self):
        with self.assertRaises(ValueError):PaperSessionManager("x").pause()
    def test_stopped_is_terminal(self):
        m=PaperSessionManager("x");m.start();m.stop()
        with self.assertRaises(ValueError):m.start()
    def test_checkpoint_restore(self):
        m=PaperSessionManager("x");m.start();m.fail();cp=m.checkpoint();r=PaperSessionManager.restore(cp)
        self.assertEqual(r.state,"FAILED");self.assertEqual(r.sequence,3)
    def test_checkpoint_tamper_blocked(self):
        m=PaperSessionManager("x");cp=m.checkpoint();cp["cash"]=1
        with self.assertRaises(ValueError):PaperSessionManager.restore(cp)
    def test_recovery_to_paused(self):
        m=PaperSessionManager("x");m.start();m.fail();m.recover("PAUSED");self.assertEqual(m.state,"PAUSED")
    def test_recovery_requires_failed(self):
        with self.assertRaises(ValueError):PaperSessionManager("x").recover()
    def test_certificate_scope(self):
        c=self.chain()[4];self.assertEqual(c["certification_scope"],"OFFLINE_RUNTIME_SCHEDULER_DEVELOPMENT_ONLY")
        self.assertFalse(c["actual_order_submission_approved"])
    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V78.15","status":"FAIL"})
        self.assertEqual(build_session_manager_foundation(self.cert,self.cfg,self.r/"bad")["status"],"FAIL")
    def test_safety_invariants(self):
        for x in self.chain():
            self.assertEqual(x["actual_orders_submitted"],0);self.assertFalse(x["network_allowed"]);self.assertFalse(x["broker_connected"])
    def test_deterministic_digest(self):
        self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
