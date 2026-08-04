import tempfile,unittest
from pathlib import Path
from web_controller.state import get_emergency,set_emergency,build_dashboard
from web_controller.actions import run_action,ALLOWED_ACTIONS

class Tests(unittest.TestCase):
    def test_emergency_default_on(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(get_emergency(Path(t))["enabled"])
    def test_emergency_toggle(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            self.assertFalse(set_emergency(root,False,"TEST")["enabled"])
    def test_dashboard_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            d=build_dashboard(Path(t))
            self.assertEqual(d["safety"]["actual_live_orders_submitted"],0)
    def test_local_only(self):
        d=build_dashboard(Path(tempfile.mkdtemp()))
        self.assertTrue(d["safety"]["local_bind_only"])
    def test_action_allowlist(self):
        self.assertIn("run_v140",ALLOWED_ACTIONS)
    def test_unknown_action_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            r=run_action(Path(t),"live_order")
            self.assertFalse(r["ok"])
    def test_emergency_blocks_cycle(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            get_emergency(root)
            r=run_action(root,"run_offline_orchestrator")
            self.assertEqual(r["error"],"EMERGENCY_STOP_ENABLED")

if __name__=="__main__":unittest.main()
