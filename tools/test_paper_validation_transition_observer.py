from pathlib import Path
import tempfile, unittest
from tools.paper_validation_transition_observer import build

class Tests(unittest.TestCase):
    def test_contract_is_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            r=build(Path(td))
            c=r["contracts"]
            self.assertFalse(c["task_changes_performed"])
            self.assertFalse(c["broker_write_performed"])
            self.assertFalse(c["paper_order_submitted"])
            self.assertFalse(c["live_order_submitted"])
            self.assertFalse(c["trading_configuration_changed"])

    def test_targets_fixed(self):
        with tempfile.TemporaryDirectory() as td:
            r=build(Path(td))
            p=r["validation_progress"]
            self.assertEqual(p["target_closed_trades"],300)
            self.assertEqual(p["target_trading_days"],10)

if __name__=="__main__":
    unittest.main()
