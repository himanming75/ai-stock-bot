import tempfile,unittest,json
from pathlib import Path
from broker_plugins.spec import validate_manifest
from broker_plugins.discovery import discover
from broker_plugins.compatibility import evaluate
from broker_plugins.loader import submit_order
from broker_plugins.reload import build_plan
from broker_plugins.engine import evaluate as run

MANIFEST={
"plugin_id":"X","display_name":"X","version":"1.0.0","api_version":"1",
"enabled":True,"read_only":True,"supports_orders":False,
"capabilities":["account_read"]
}

class Tests(unittest.TestCase):
    def test_manifest_valid(self): self.assertTrue(validate_manifest(MANIFEST)["valid"])
    def test_manifest_write_blocked(self):
        bad={**MANIFEST,"supports_orders":True}
        self.assertFalse(validate_manifest(bad)["valid"])
    def test_discovery(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); p=root/"broker_plugin_packages/x"; p.mkdir(parents=True)
            (p/"manifest.json").write_text(json.dumps(MANIFEST))
            self.assertEqual(len(discover(root)),1)
    def test_compatibility(self):
        plugin={"manifest":MANIFEST,"validation":{"valid":True}}
        self.assertTrue(evaluate(plugin)["compatible"])
    def test_submit_order_blocked(self):
        self.assertEqual(submit_order({})["error"],"PLUGIN_ORDER_SUBMISSION_DISABLED")
    def test_reload_no_write(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(build_plan(Path(t),["X"])["broker_write_enabled"])
    def test_engine_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(run(Path(t))["actual_live_orders_submitted"],0)

if __name__=="__main__": unittest.main()
