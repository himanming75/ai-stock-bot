import json
import tempfile
import unittest
from pathlib import Path

from shadow_counterfactual_v76_v80 import ShadowParameterCounterfactualPack


class Tests(unittest.TestCase):
    def setup_root(self, root: Path):
        ledger = (
            root
            / "runtime/closed_trade_outcome_v41_v45/"
              "closed_trade_outcomes.jsonl"
        )
        ledger.parent.mkdir(parents=True, exist_ok=True)

        rows = [
            {
                "trade_id": "T1",
                "symbol": "AAPL",
                "entry_price": 100,
                "exit_price": 110,
                "quantity": 1,
                "realized_pl": 10,
                "signal_confidence": 0.90,
                "post_exit_1h_return": 0.01,
                "post_exit_4h_return": 0.02
            },
            {
                "trade_id": "T2",
                "symbol": "SPY",
                "entry_price": 100,
                "exit_price": 95,
                "quantity": 1,
                "realized_pl": -5,
                "signal_confidence": 0.75,
                "post_exit_1h_return": -0.01,
                "post_exit_4h_return": 0.01
            }
        ]

        with ledger.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")

    def test_scenario_generator(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            r = ShadowParameterCounterfactualPack(
                root
            ).v76_parameter_scenario_generator()
            self.assertFalse(r["actual_parameter_changes"])

    def test_entry_threshold(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = ShadowParameterCounterfactualPack(
                root
            ).v77_entry_threshold_counterfactual()
            self.assertEqual(r["trade_count"], 2)

    def test_exit_does_not_fabricate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = ShadowParameterCounterfactualPack(
                root
            ).v78_exit_hold_counterfactual()
            self.assertFalse(r["fabricated_path_data"])

    def test_notional_does_not_change_actual(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = ShadowParameterCounterfactualPack(
                root
            ).v79_notional_risk_scenarios()
            self.assertFalse(r["actual_notional_changed"])

    def test_validation_advisory(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = ShadowParameterCounterfactualPack(
                root
            ).v80_counterfactual_validation_summary()
            self.assertEqual(r["deployment_effect"], "ADVISORY_ONLY")

    def test_missing_data_still_runs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            r = ShadowParameterCounterfactualPack(root).run()
            self.assertEqual(r["status"], "PASS")

    def test_outputs_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            ShadowParameterCounterfactualPack(root).run()
            rt = root / "runtime/shadow_counterfactual_v76_v80"
            self.assertTrue(
                (rt / "latest_counterfactual_report.json").exists()
            )
            self.assertTrue(
                (rt / "counterfactual_scenario_dataset.json").exists()
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
