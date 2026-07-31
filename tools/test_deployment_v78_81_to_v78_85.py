import tempfile,unittest
from pathlib import Path
from deployment.deployment_pipeline_v78_81_85 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.r=Path(self.t.name)
        self.cert=self.r/"cert.json"
        self.cfg=self.r/"cfg.json"
        write_json(self.cert,{
            "stage":"V78.80","status":"PASS",
            "certification_scope":"OFFLINE_DEPLOYMENT_PACKAGING_DEVELOPMENT_ONLY",
            "champion_candidate":{"candidate_id":"abc"}
        })
        files={
            "a/report.json":"{\"ok\":true}\n",
            "a/report.csv":"x,y\n1,2\n",
            "a/report.md":"# Report\n",
        }
        for rel,text in files.items():
            p=self.r/rel
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(text,encoding="utf-8")
        write_json(self.cfg,{
            "deployment":{
                "release_id":"RID","release_version":"1.0",
                "target_environment":"offline","allow_live_deployment":False,
                "required_artifacts":list(files)
            }
        })

    def tearDown(self):
        self.t.cleanup()

    def chain(self):
        o81=self.r/"o81"
        a=build_deployment_foundation(self.cert,self.cfg,o81)
        o82=self.r/"o82"
        b=run_deployment_package_builder(
            self.r,o81/"deployment_foundation_v78_81.json",o82)
        o83=self.r/"o83"
        c=run_deployment_validation(
            self.r,o81/"deployment_foundation_v78_81.json",
            o82/"deployment_package_builder_v78_82.json",o83)
        o84=self.r/"o84"
        d=run_deployment_safety_gate(
            o81/"deployment_foundation_v78_81.json",
            o82/"deployment_package_builder_v78_82.json",
            o83/"deployment_validation_v78_83.json",o84)
        o85=self.r/"o85"
        e=issue_deployment_certificate(
            o81/"deployment_foundation_verification_v78_81.json",
            o82/"deployment_package_builder_verification_v78_82.json",
            o83/"deployment_validation_verification_v78_83.json",
            o84/"deployment_safety_gate_verification_v78_84.json",
            o81/"deployment_foundation_v78_81.json",
            o82/"deployment_package_builder_v78_82.json",o85)
        return a,b,c,d,e

    def test_full_chain(self):
        self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))

    def test_artifact_hash_tamper_detected(self):
        artifact=asdict(inspect_artifact(self.r,"a/report.json"))
        (self.r/"a/report.json").write_text("tampered",encoding="utf-8")
        self.assertFalse(verify_artifact(self.r,artifact))

    def test_missing_artifact_blocked(self):
        cfg=load_json(self.cfg)
        cfg["deployment"]["required_artifacts"].append("missing.json")
        write_json(self.cfg,cfg)
        o=self.r/"bad"
        build_deployment_foundation(self.cert,self.cfg,o)
        result=run_deployment_package_builder(
            self.r,o/"deployment_foundation_v78_81.json",self.r/"bad2")
        self.assertEqual(result["status"],"FAIL")

    def test_manifest_hash_deterministic(self):
        a=inspect_artifact(self.r,"a/report.json")
        b=inspect_artifact(self.r,"a/report.json")
        self.assertEqual(a.sha256,b.sha256)
        self.assertEqual(a.artifact_id,b.artifact_id)

    def test_live_deployment_flag_blocked(self):
        cfg=load_json(self.cfg)
        cfg["deployment"]["allow_live_deployment"]=True
        write_json(self.cfg,cfg)
        result=build_deployment_foundation(self.cert,self.cfg,self.r/"badlive")
        self.assertEqual(result["status"],"FAIL")

    def test_target_environment_blocked(self):
        cfg=load_json(self.cfg)
        cfg["deployment"]["target_environment"]="live"
        write_json(self.cfg,cfg)
        result=build_deployment_foundation(self.cert,self.cfg,self.r/"badenv")
        self.assertEqual(result["status"],"FAIL")

    def test_certificate_scope(self):
        c=self.chain()[4]
        self.assertEqual(c["certification_scope"],"OFFLINE_OPERATION_RUNTIME_DEVELOPMENT_ONLY")
        self.assertFalse(c["live_deployment_approved"])

    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V78.80","status":"FAIL"})
        self.assertEqual(
            build_deployment_foundation(self.cert,self.cfg,self.r/"badcert")["status"],
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
