from pathlib import Path
import tempfile, unittest
from tools.paper_validation_transition_observer import build, normalize_state

class Tests(unittest.TestCase):
    def test_numeric_task_states(self):
        self.assertEqual(normalize_state(1),"Disabled")
        self.assertEqual(normalize_state(3),"Ready")
        self.assertEqual(normalize_state(4),"Running")
        self.assertEqual(normalize_state("1"),"Disabled")
        self.assertEqual(normalize_state("Ready"),"Ready")

    def test_contract_is_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            r=build(Path(td))
            c=r["contracts"]
            self.assertFalse(c["task_changes_performed_by_observer"])
            self.assertFalse(c["broker_write_performed"])
            self.assertFalse(c["paper_order_submitted"])
            self.assertFalse(c["live_order_submitted"])
            self.assertFalse(c["trading_configuration_changed"])
            self.assertFalse(c["strategy_parameter_changed"])

    def test_targets_fixed(self):
        with tempfile.TemporaryDirectory() as td:
            p=build(Path(td))["validation_progress"]
            self.assertEqual(p["target_closed_trades"],300)
            self.assertEqual(p["target_trading_days"],10)

if __name__=="__main__":
    unittest.main()
