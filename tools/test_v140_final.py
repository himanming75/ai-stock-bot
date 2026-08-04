import tempfile,unittest
from pathlib import Path
from v140_autonomous_release.integration import summarize
from v140_autonomous_release.safety import evaluate as safety
from v140_autonomous_release.certificate import build
from v140_autonomous_release.engine import evaluate

class Tests(unittest.TestCase):
    def test_summary(self):
        s=summarize({"x":{"stage":"V1","state":"S","status":"PASS"}})
        self.assertTrue(s["x"]["present"])
    def test_safety_pass(self):
        src={"x":{"status":"PASS","actual_live_orders_submitted":0}}
        p={"live_network_enabled":False,"live_submission_enabled":False,
           "manual_live_enable_required":True,"default_mode":"PAPER",
           "kill_switch_default_enabled":True}
        r=safety(src,p)
        self.assertTrue(r["passed"])
    def test_safety_blocks_live_history(self):
        src={"x":{"status":"PASS","actual_live_orders_submitted":1}}
        p={"live_network_enabled":False,"live_submission_enabled":False,
           "manual_live_enable_required":True,"default_mode":"PAPER",
           "kill_switch_default_enabled":True}
        self.assertFalse(safety(src,p)["passed"])
    def test_certificate(self):
        c=build({"passed":True},{"x":1})
        self.assertEqual(len(c["certificate_sha256"]),64)
    def test_missing_sources(self):
        with tempfile.TemporaryDirectory() as t:
            r=evaluate(Path(t))
            self.assertEqual(r["state"],"V140_FINAL_AUTONOMOUS_RELEASE_REVIEW_REQUIRED")
    def test_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"],0)

if __name__=="__main__":unittest.main()
