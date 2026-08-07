from pathlib import Path
import tempfile, unittest
from tools.paper_first_session_start_confirmation import build

class Tests(unittest.TestCase):
    def test_read_only_contract(self):
        with tempfile.TemporaryDirectory() as td:
            r=build(Path(td))
            c=r["contracts"]
            self.assertTrue(c["broker_read_only"])
            self.assertFalse(c["broker_write_performed"])
            self.assertFalse(c["paper_order_submitted_by_observer"])
            self.assertFalse(c["live_order_submitted"])
            self.assertFalse(c["task_changes_performed_by_observer"])
            self.assertFalse(c["strategy_parameter_changed"])

    def test_fixed_validation_targets(self):
        with tempfile.TemporaryDirectory() as td:
            r=build(Path(td))
            self.assertEqual(r["validation_progress"]["target_closed_trades"],300)
            self.assertEqual(r["validation_progress"]["target_trading_days"],10)

if __name__=="__main__":
    unittest.main()
