import tempfile,unittest
from pathlib import Path
from release_acceptance.release_acceptance_pipeline_v78_96_100 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.r=Path(self.t.name)
        self.cert=self.r/"cert.json"
        self.cfg=self.r/"cfg.json"
        write_json(self.cert,{
            "stage":"V78.95","status":"PASS",
            "certification_scope":"COMPLETE_OFFLINE_PAPER_TRADING_SYSTEM_ONLY",
            "champion_candidate":{"candidate_id":"802493bbc77a"},
            "system_id":"SYS","system_version":"78.95",
            "release_id":"RID","runtime_id":"RT","module_chain_head":"MHEAD"
        })
        artifacts={}
        for i,name in enumerate((
            "final_system_certificate_v78_95.json",
            "final_system_summary.json",
            "operation_runtime_certificate.json",
            "deployment_certificate.json",
            "deployment_manifest_v78_82.json",
            "reporting_certificate.json",
            "report_manifest_v78_78.json",
            "performance_report_v78_78.json",
            "equity_curve_v78_78.csv",
            "performance_report_v78_78.md",
        ),1):
            rel=f"artifacts/{name}"
            p=self.r/rel
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(f"artifact-{i}-{name}\n",encoding="utf-8")
            artifacts[rel]=True
        write_json(self.cfg,{
            "release_acceptance":{
                "release_name":"FINAL","release_version":"78.100",
                "required_artifacts":list(artifacts),
                "acceptance_checks":["a","b"],
                "allow_live_release":False
            }
        })

    def tearDown(self):
        self.t.cleanup()

    def chain(self):
        o96=self.r/"o96"
        a=build_release_acceptance_foundation(self.cert,self.cfg,o96)
        o97=self.r/"o97"
        b=run_release_acceptance_checklist(
            self.r,o96/"release_acceptance_foundation_v78_96.json",o97)
        o98=self.r/"o98"
        c=run_release_artifact_verification(
            self.r,
            o96/"release_acceptance_foundation_v78_96.json",
            o97/"release_acceptance_checklist_v78_97.json",o98)
        o99=self.r/"o99"
        d=run_release_acceptance_safety_gate(
            o96/"release_acceptance_foundation_v78_96.json",
            o97/"release_acceptance_checklist_v78_97.json",
            o98/"release_artifact_verification_v78_98.json",o99)
        o100=self.r/"o100"
        e=issue_final_release_certificate(
            o96/"release_acceptance_foundation_verification_v78_96.json",
            o97/"release_acceptance_checklist_verification_v78_97.json",
            o98/"release_artifact_verification_verification_v78_98.json",
            o99/"release_acceptance_safety_gate_verification_v78_99.json",
            o96/"release_acceptance_foundation_v78_96.json",
            o98/"release_artifact_verification_v78_98.json",o100)
        return a,b,c,d,e

    def test_full_chain(self):
        self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))

    def test_artifact_tamper_blocked(self):
        rec=build_artifact_record(1,self.r,"artifacts/final_system_certificate_v78_95.json","")
        (self.r/rec.relative_path).write_text("tampered",encoding="utf-8")
        with self.assertRaises(ValueError):
            verify_artifact_chain(self.r,[rec])

    def test_missing_artifact_blocked(self):
        cfg=load_json(self.cfg)
        cfg["release_acceptance"]["required_artifacts"].append("missing.json")
        write_json(self.cfg,cfg)
        o=self.r/"bad96"
        build_release_acceptance_foundation(self.cert,self.cfg,o)
        result=run_release_acceptance_checklist(
            self.r,o/"release_acceptance_foundation_v78_96.json",self.r/"bad97")
        self.assertEqual(result["status"],"FAIL")

    def test_chain_record_tamper_blocked(self):
        rec=build_artifact_record(1,self.r,"artifacts/final_system_certificate_v78_95.json","")
        bad=AcceptanceArtifact(**{**asdict(rec),"artifact_type":"tampered"})
        with self.assertRaises(ValueError):
            verify_artifact_chain(self.r,[bad])

    def test_live_release_blocked(self):
        cfg=load_json(self.cfg)
        cfg["release_acceptance"]["allow_live_release"]=True
        write_json(self.cfg,cfg)
        self.assertEqual(
            build_release_acceptance_foundation(self.cert,self.cfg,self.r/"live")["status"],
            "FAIL"
        )

    def test_certificate_scope(self):
        c=self.chain()[4]
        self.assertEqual(c["certification_scope"],"FINAL_OFFLINE_PAPER_TRADING_RELEASE_ONLY")
        self.assertTrue(c["release_ready"])
        self.assertFalse(c["live_release_approved"])

    def test_invalid_final_certificate_rejected(self):
        write_json(self.cert,{"stage":"V78.95","status":"FAIL"})
        self.assertEqual(
            build_release_acceptance_foundation(self.cert,self.cfg,self.r/"badcert")["status"],
            "FAIL"
        )

    def test_manifest_has_chain_head(self):
        c=self.chain()[2]
        self.assertTrue(c["final_release_manifest"]["artifact_chain_head"])
        self.assertEqual(c["final_release_manifest"]["artifact_count"],10)

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
