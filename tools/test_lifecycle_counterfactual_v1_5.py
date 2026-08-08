from pathlib import Path
import unittest
class Tests(unittest.TestCase):
    def setUp(self):
        self.text=Path("tools/build_real_market_multitimeframe_shadow.py").read_text(encoding="utf-8")
    def test_counterfactual_mode_extends_existing_file(self):
        self.assertIn("def rolling_counterfactual(",self.text)
        self.assertIn('"counterfactual"',self.text)
    def test_only_evidence_based_scenarios(self):
        for name in ("BASELINE","EXCLUDE_MSFT","NO_NEW_ENTRY_AFTER_14_ET","EXCLUDE_MSFT_AND_NO_ENTRY_AFTER_14_ET","MAX_HOLD_20M","MAX_HOLD_45M","MAX_HOLD_60M"):
            self.assertIn(name,self.text)
    def test_reuses_existing_lifecycle_simulator(self):
        self.assertIn("report=rolling_lifecycle(root)",self.text)
    def test_production_never_changed(self):
        self.assertIn('"production_parameters_changed":False',self.text)
        self.assertIn('"automatic_promotion":False',self.text)
        self.assertIn('"automatic_parameter_optimization":False',self.text)
        self.assertNotIn("client.submit_order",self.text)
        self.assertNotIn("TradingClient(",self.text)
    def test_runtime_baseline_artifacts_restored(self):
        self.assertIn("_counterfactual_snapshot_files",self.text)
        self.assertIn("_counterfactual_restore_files",self.text)
if __name__=="__main__":
    unittest.main()
