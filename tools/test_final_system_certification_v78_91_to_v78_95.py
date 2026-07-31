import tempfile,unittest
from pathlib import Path
from final_system_certification.final_system_certification_pipeline_v78_91_95 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.r=Path(self.t.name)
        self.runtime_cert=self.r/"runtime_cert.json"
        self.cfg=self.r/"cfg.json"
        write_json(self.runtime_cert,{
            "stage":"V78.90","status":"PASS",
            "certification_scope":"OFFLINE_FINAL_SYSTEM_CERTIFICATION_DEVELOPMENT_ONLY",
            "champion_candidate":{"candidate_id":"802493bbc77a"},
            "release_id":"RID","runtime_id":"RT"
        })
        cert_paths=[]
        for i,stage in enumerate(("V78.65","V78.70","V78.75","V78.80","V78.85","V78.90"),1):
            rel=f"certs/c{i}.json"
            p=self.r/rel
            write_json(p,{
                "stage":stage,"status":"PASS",
                "certification_scope":f"SCOPE-{stage}",
                "certificate_sha256":f"sha-{stage}"
            })
            cert_paths.append(rel)
        summaries=[
            "release/v78_65/output/fill_portfolio_bridge_pipeline_summary_v78_61_to_v78_65.json",
            "release/v78_70/output/audit_reconciliation_pipeline_summary_v78_66_to_v78_70.json",
            "release/v78_75/output/performance_accounting_pipeline_summary_v78_71_to_v78_75.json",
            "release/v78_80/output/reporting_pipeline_summary_v78_76_to_v78_80.json",
            "release/v78_85/output/deployment_pipeline_summary_v78_81_to_v78_85.json",
            "release/v78_90/output/operation_runtime_pipeline_summary_v78_86_to_v78_90.json",
        ]
        for rel in summaries:
            p=self.r/rel
            doc={"status":"PASS","actual_orders_submitted":0,"network_allowed":False,"broker_connected":False}
            doc["pipeline_sha256"]=digest_json(doc)
            write_json(p,doc)
        write_json(self.cfg,{
            "final_system_certification":{
                "system_id":"SYS","system_version":"78.95",
                "required_certificates":cert_paths,
                "allow_live_activation":False
            }
        })

    def tearDown(self):
        self.t.cleanup()

    def chain(self):
        o91=self.r/"o91"
        a=build_final_system_certification_foundation(self.runtime_cert,self.cfg,o91)
        o92=self.r/"o92"
        b=run_cross_module_integrity_audit(
            self.r,o91/"final_system_certification_foundation_v78_91.json",o92)
        o93=self.r/"o93"
        c=run_end_to_end_replay_validation(
            self.r,
            o91/"final_system_certification_foundation_v78_91.json",
            o92/"cross_module_integrity_audit_v78_92.json",o93)
        o94=self.r/"o94"
        d=run_final_system_safety_gate(
            o91/"final_system_certification_foundation_v78_91.json",
            o92/"cross_module_integrity_audit_v78_92.json",
            o93/"end_to_end_replay_validation_v78_93.json",o94)
        o95=self.r/"o95"
        e=issue_final_system_certificate(
            o91/"final_system_certification_foundation_verification_v78_91.json",
            o92/"cross_module_integrity_audit_verification_v78_92.json",
            o93/"end_to_end_replay_validation_verification_v78_93.json",
            o94/"final_system_safety_gate_verification_v78_94.json",
            o91/"final_system_certification_foundation_v78_91.json",
            o92/"cross_module_integrity_audit_v78_92.json",o95)
        return a,b,c,d,e

    def test_full_chain(self):
        self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))

    def test_module_chain_tamper_blocked(self):
        cert={"stage":"V1","status":"PASS","certification_scope":"S"}
        r1=build_module_record(1,"V1","a.json",cert,"")
        bad=ModuleCertificateRecord(**{**asdict(r1),"certificate_status":"FAIL"})
        with self.assertRaises(ValueError):
            verify_module_chain([bad])

    def test_missing_certificate_blocked(self):
        cfg=load_json(self.cfg)
        cfg["final_system_certification"]["required_certificates"].append("missing.json")
        write_json(self.cfg,cfg)
        o=self.r/"bad"
        build_final_system_certification_foundation(self.runtime_cert,self.cfg,o)
        result=run_cross_module_integrity_audit(
            self.r,o/"final_system_certification_foundation_v78_91.json",self.r/"bad2")
        self.assertEqual(result["status"],"FAIL")

    def test_replay_hash_tamper_detected(self):
        p=self.r/"release/v78_65/output/fill_portfolio_bridge_pipeline_summary_v78_61_to_v78_65.json"
        doc=load_json(p);doc["status"]="FAIL";write_json(p,doc)
        o91=self.r/"tamper91"
        build_final_system_certification_foundation(self.runtime_cert,self.cfg,o91)
        o92=self.r/"tamper92"
        run_cross_module_integrity_audit(self.r,o91/"final_system_certification_foundation_v78_91.json",o92)
        result=run_end_to_end_replay_validation(
            self.r,o91/"final_system_certification_foundation_v78_91.json",
            o92/"cross_module_integrity_audit_v78_92.json",self.r/"tamper93")
        self.assertEqual(result["status"],"FAIL")

    def test_live_activation_blocked(self):
        cfg=load_json(self.cfg)
        cfg["final_system_certification"]["allow_live_activation"]=True
        write_json(self.cfg,cfg)
        self.assertEqual(
            build_final_system_certification_foundation(self.runtime_cert,self.cfg,self.r/"live")["status"],
            "FAIL"
        )

    def test_certificate_scope(self):
        c=self.chain()[4]
        self.assertEqual(c["certification_scope"],"COMPLETE_OFFLINE_PAPER_TRADING_SYSTEM_ONLY")
        self.assertFalse(c["live_activation_approved"])

    def test_invalid_runtime_certificate_rejected(self):
        write_json(self.runtime_cert,{"stage":"V78.90","status":"FAIL"})
        self.assertEqual(
            build_final_system_certification_foundation(self.runtime_cert,self.cfg,self.r/"badcert")["status"],
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
