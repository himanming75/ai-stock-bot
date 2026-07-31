import tempfile,unittest
from pathlib import Path
from live_readiness.live_readiness_pipeline_v77_91_95 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
        self.cert=self.r/"cert.json";self.cfg=self.r/"cfg.json"
        write_json(self.cert,{"stage":"V77.90","status":"PASS",
          "certification_scope":"LIVE_READINESS_AUDIT_ELIGIBILITY_ONLY",
          "champion_candidate":{"candidate_id":"abc","parameters":{"fast_window":20,"slow_window":50},
          "metrics":{"total_return":0.08}}})
        write_json(self.cfg,{
          "operational_controls":{"kill_switch_defined":True,"max_position_limit_defined":True,
          "max_daily_loss_limit_defined":True,"order_rate_limit_defined":True,
          "audit_logging_enabled":True,"manual_override_required":True},
          "recovery_controls":{"checkpoint_restore_supported":True,"corruption_detection_supported":True,
          "replay_supported":True,"idempotency_guard_supported":True,"disconnect_halt_supported":True,
          "risk_breach_kill_supported":True,"manual_stop_supported":True},
          "security_controls":{"secrets_externalized":True,"credentials_not_in_repository":True,
          "network_default_deny":True},
          "deployment_controls":{"paper_mode_default":True,"live_mode_default_disabled":True,
          "broker_adapter_not_enabled":True}})
    def tearDown(self):self.t.cleanup()
    def chain(self):
        o91=self.r/"o91";a=build_live_readiness_audit_engine(self.cert,self.cfg,o91)
        o92=self.r/"o92";b=build_operational_safety_checklist(o91/"live_readiness_audit_engine_v77_91.json",o92)
        o93=self.r/"o93";c=run_recovery_kill_switch_audit(o91/"live_readiness_audit_engine_v77_91.json",o93)
        o94=self.r/"o94";d=run_live_readiness_safety_gate(
          o92/"operational_safety_checklist_v77_92.json",
          o93/"recovery_kill_switch_audit_v77_93.json",
          o91/"live_readiness_audit_engine_v77_91.json",o94)
        o95=self.r/"o95";e=issue_live_readiness_certificate(
          o91/"live_readiness_audit_engine_verification_v77_91.json",
          o92/"operational_safety_checklist_verification_v77_92.json",
          o93/"recovery_kill_switch_audit_verification_v77_93.json",
          o94/"live_readiness_safety_gate_verification_v77_94.json",
          o91/"live_readiness_audit_engine_v77_91.json",o95)
        return a,b,c,d,e
    def test_full_chain(self):self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))
    def test_checklist_count(self):self.assertEqual(self.chain()[1]["check_count"],12)
    def test_recovery_scenarios(self):self.assertEqual(self.chain()[2]["scenario_count"],6)
    def test_certificate_scope(self):
        cert=self.chain()[4]
        self.assertEqual(cert["certification_scope"],"BROKER_INTEGRATION_SKELETON_ELIGIBILITY_ONLY")
        self.assertFalse(cert["live_trading_approved"])
        self.assertFalse(cert["broker_connection_approved"])
    def test_safety_invariants(self):
        for x in self.chain():
            self.assertEqual(x["actual_orders_submitted"],0)
            self.assertFalse(x["network_allowed"])
            self.assertFalse(x["broker_connected"])
    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V77.90","status":"FAIL"})
        self.assertEqual(build_live_readiness_audit_engine(self.cert,self.cfg,self.r/"bad")["status"],"FAIL")
    def test_missing_kill_switch_blocked(self):
        cfg=load_json(self.cfg);cfg["operational_controls"]["kill_switch_defined"]=False;write_json(self.cfg,cfg)
        chain=self.chain()
        self.assertEqual(chain[1]["status"],"FAIL")
        self.assertEqual(chain[2]["status"],"FAIL")
    def test_live_mode_enabled_blocked(self):
        cfg=load_json(self.cfg);cfg["deployment_controls"]["live_mode_default_disabled"]=False;write_json(self.cfg,cfg)
        self.assertEqual(self.chain()[1]["status"],"FAIL")
    def test_recovery_failure_blocked(self):
        cfg=load_json(self.cfg);cfg["recovery_controls"]["checkpoint_restore_supported"]=False;write_json(self.cfg,cfg)
        self.assertEqual(self.chain()[2]["status"],"FAIL")
    def test_deterministic_digest(self):
        self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
