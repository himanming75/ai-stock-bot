from __future__ import annotations
import inspect, tempfile, unittest
from pathlib import Path
from model_governance_optimization.io import write_json
from model_governance_optimization.service import ModelGovernanceOptimizationService

class Tests(unittest.TestCase):
    def evaluate(self, root):
        candidates = root / "candidates.json"
        champion = root / "champion.json"
        policy = root / "policy.json"
        write_json(candidates, {"items": [{
            "model_id": "challenger", "sample_count": 100, "train_score": 0.70,
            "test_score": 0.68, "fold_scores": [0.66,0.68,0.69],
            "sharpe_like": 1.2, "balanced_accuracy": 0.70,
            "max_drawdown": -0.08, "calibration_error": 0.10, "turnover": 0.2
        }]})
        write_json(champion, {"champion": {
            "model_id": "champion", "sample_count": 100, "train_score": 0.60,
            "test_score": 0.58, "fold_scores": [0.57,0.58,0.59],
            "sharpe_like": 0.9, "balanced_accuracy": 0.60,
            "max_drawdown": -0.10, "calibration_error": 0.12, "turnover": 0.2
        }})
        write_json(policy, {
            "minimum_sample_count": 50, "minimum_test_score": 0.55,
            "maximum_drawdown": 0.20, "maximum_calibration_error": 0.20,
            "minimum_promotion_improvement": 0.03
        })
        return ModelGovernanceOptimizationService().evaluate(
            candidates_path=candidates, champion_path=champion,
            policy_path=policy, output_dir=root / "out"
        )

    def test_pass(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.evaluate(Path(d))["status"], "PASS")

    def test_recommendation(self):
        with tempfile.TemporaryDirectory() as d:
            result = self.evaluate(Path(d))
            self.assertIn(result["promotion_recommendation"]["recommendation"],
                          {"RECOMMEND_CHALLENGER_PROMOTION_REVIEW","KEEP_CURRENT_CHAMPION"})

    def test_no_auto_promotion(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(self.evaluate(Path(d))["automatic_promotion_enabled"])

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.evaluate(root)
            self.assertTrue((root / "out/model_governance_ledger.jsonl").exists())

    def test_zero_order_contract(self):
        source = inspect.getsource(ModelGovernanceOptimizationService)
        self.assertIn('"actual_broker_write_performed": False', source)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
        self.assertIn('"actual_live_orders_submitted": 0', source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
