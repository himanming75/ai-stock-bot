from __future__ import annotations
import inspect
import tempfile
import unittest
from pathlib import Path

from ai_decision_engine.io import write_json
from ai_decision_engine.service import AIDecisionEngineService

class Tests(unittest.TestCase):
    def inputs(self, root: Path, risk_level="NORMAL"):
        strategy = root / "strategy.json"
        write_json(
            strategy,
            {
                "status": "PASS",
                "framework_fingerprint": "strategy-1",
                "strategy_results": [
                    {
                        "strategy": "momentum",
                        "symbol": "SPY",
                        "status": "PASS",
                        "signal": "BUY",
                        "score": "30",
                    },
                    {
                        "strategy": "trend",
                        "symbol": "SPY",
                        "status": "PASS",
                        "signal": "BUY",
                        "score": "20",
                    },
                    {
                        "strategy": "mean_reversion",
                        "symbol": "SPY",
                        "status": "PASS",
                        "signal": "SELL",
                        "score": "5",
                    },
                ],
                "symbol_decisions": [
                    {
                        "symbol": "SPY",
                        "status": "PASS",
                        "signal": "BUY",
                        "combined_score": "15",
                    }
                ],
            },
        )
        risk = root / "risk.json"
        write_json(
            risk,
            {
                "risk_level": risk_level,
                "portfolio_risk_score": "5",
                "alert_count": 0,
            },
        )
        tf = root / "tf.json"
        write_json(
            tf,
            {
                "symbols": {
                    "SPY": {
                        "1m": "BUY",
                        "5m": "BUY",
                        "15m": "BUY",
                        "60m": "BUY",
                    }
                }
            },
        )
        policy = root / "policy.json"
        write_json(
            policy,
            {
                "score_scale": "4",
                "agreement_weight": "0.55",
                "magnitude_weight": "0.45",
                "minimum_confidence": "50",
                "minimum_agreement_percent": "60",
                "allowed_risk_levels": ["NORMAL"],
                "risk_penalty": {
                    "NORMAL": "0",
                    "WARNING": "20",
                    "CRITICAL": "100",
                    "UNKNOWN": "35",
                },
                "required_timeframes": ["1m", "5m", "15m", "60m"],
                "require_complete_timeframes": True,
            },
        )
        return strategy, risk, tf, policy

    def evaluate(self, root, risk_level="NORMAL"):
        paths = self.inputs(root, risk_level)
        return AIDecisionEngineService().evaluate(
            strategy_path=paths[0],
            risk_path=paths[1],
            timeframe_path=paths[2],
            policy_path=paths[3],
            output_dir=root / "out",
        )

    def test_buy_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory))
            self.assertEqual(result["candidate_count"], 1)
            self.assertEqual(
                result["candidate_queue"][0]["decision"],
                "BUY",
            )

    def test_risk_blocks_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(
                Path(directory), risk_level="CRITICAL"
            )
            self.assertEqual(result["candidate_count"], 0)
            self.assertEqual(
                result["decisions"][0]["decision"],
                "HOLD",
            )

    def test_missing_strategy_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, risk, tf, policy = self.inputs(root)
            missing = root / "missing.json"
            result = AIDecisionEngineService().evaluate(
                strategy_path=missing,
                risk_path=risk,
                timeframe_path=tf,
                policy_path=policy,
                output_dir=root / "out",
            )
            self.assertEqual(
                result["status"], "INSUFFICIENT_INPUT"
            )

    def test_output_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.evaluate(root)
            self.assertTrue(
                (root / "out/ai_decision_dashboard.json").exists()
            )
            self.assertTrue(
                (root / "out/ai_decision_ledger.jsonl").exists()
            )

    def test_no_network_or_orders(self):
        source = inspect.getsource(AIDecisionEngineService)
        self.assertIn('"actual_ai_network_used": False', source)
        self.assertIn('"actual_order_ticket_created": False', source)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
        self.assertIn('"actual_live_orders_submitted": 0', source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
