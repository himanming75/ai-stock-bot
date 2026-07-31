import tempfile,unittest
from pathlib import Path
from operation_runtime.operation_runtime_pipeline_v78_86_90 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.r=Path(self.t.name)
        self.cert=self.r/"cert.json"
        self.cfg=self.r/"cfg.json"
        write_json(self.cert,{
            "stage":"V78.85","status":"PASS",
            "certification_scope":"OFFLINE_OPERATION_RUNTIME_DEVELOPMENT_ONLY",
            "champion_candidate":{"candidate_id":"abc"},
            "release_id":"RID"
        })
        write_json(self.cfg,{
            "operation_runtime":{
                "runtime_id":"RT","max_restarts":2,
                "heartbeat_count":2,"allow_live_runtime":False
            }
        })

    def tearDown(self):
        self.t.cleanup()

    def chain(self):
        o86=self.r/"o86"
        a=build_operation_runtime_foundation(self.cert,self.cfg,o86)
        o87=self.r/"o87"
        b=run_runtime_health_heartbeat(
            o86/"operation_runtime_foundation_v78_86.json",o87)
        o88=self.r/"o88"
        c=run_runtime_recovery_restart(
            o86/"operation_runtime_foundation_v78_86.json",
            o87/"runtime_health_heartbeat_v78_87.json",o88)
        o89=self.r/"o89"
        d=run_operation_runtime_safety_gate(
            o86/"operation_runtime_foundation_v78_86.json",
            o87/"runtime_health_heartbeat_v78_87.json",
            o88/"runtime_recovery_restart_v78_88.json",o89)
        o90=self.r/"o90"
        e=issue_operation_runtime_certificate(
            o86/"operation_runtime_foundation_verification_v78_86.json",
            o87/"runtime_health_heartbeat_verification_v78_87.json",
            o88/"runtime_recovery_restart_verification_v78_88.json",
            o89/"operation_runtime_safety_gate_verification_v78_89.json",
            o86/"operation_runtime_foundation_v78_86.json",o90)
        return a,b,c,d,e

    def test_full_chain(self):
        self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))

    def test_valid_start_heartbeat_checkpoint(self):
        rt=OfflineOperationRuntime("rt",2)
        rt.start();rt.heartbeat();cp=rt.checkpoint()
        self.assertEqual(rt.state,"RUNNING")
        self.assertEqual(cp["checkpoint_sequence"],1)

    def test_invalid_transition_blocked(self):
        rt=OfflineOperationRuntime("rt",2)
        with self.assertRaises(ValueError):
            rt.transition("RUNNING")

    def test_recovery_requires_checkpoint(self):
        rt=OfflineOperationRuntime("rt",2)
        rt.start();rt.fail("x")
        with self.assertRaises(ValueError):
            rt.recover()

    def test_checkpoint_tamper_blocked(self):
        rt=OfflineOperationRuntime("rt",2)
        rt.start();rt.checkpoint();rt.checkpoints[-1]["state"]="tampered";rt.fail("x")
        with self.assertRaises(ValueError):
            rt.recover()

    def test_restart_limit(self):
        rt=OfflineOperationRuntime("rt",1)
        rt.start();rt.checkpoint();rt.fail("x");rt.recover()
        rt.state="FAILED"
        with self.assertRaises(ValueError):
            rt.recover()

    def test_event_chain_tamper_blocked(self):
        rt=OfflineOperationRuntime("rt",1)
        rt.start();rt.heartbeat()
        rt.events[0]["state"]="tampered"
        with self.assertRaises(ValueError):
            verify_event_chain(rt.events)

    def test_certificate_scope(self):
        c=self.chain()[4]
        self.assertEqual(c["certification_scope"],"OFFLINE_FINAL_SYSTEM_CERTIFICATION_DEVELOPMENT_ONLY")
        self.assertFalse(c["actual_order_submission_approved"])

    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V78.85","status":"FAIL"})
        self.assertEqual(
            build_operation_runtime_foundation(self.cert,self.cfg,self.r/"bad")["status"],
            "FAIL"
        )

    def test_safety_invariants(self):
        for x in self.chain():
            self.assertEqual(x["actual_orders_submitted"],0)
            self.assertFalse(x["network_allowed"])
            self.assertFalse(x["broker_connected"])
            self.assertFalse(x["live_deployment_approved"])

    def test_deterministic_digest(self):
        self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))

if __name__=="__main__":
    unittest.main()
