from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from smart_safe_guard import SmartSafeTradingGuard


class Tests(unittest.TestCase):
    def evaluate(self, overrides=None, policy_overrides=None):
        overrides = overrides or {}
        policy_overrides = policy_overrides or {}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            policy = {
                "mode": "SHADOW",
                "minimum_confidence": 0.8,
                "minimum_consensus_score": 0.75,
                "minimum_reward_risk": 1.5,
                "maximum_order_notional": 100,
                "maximum_daily_orders": 1,
                "maximum_open_positions": 2,
                "maximum_daily_loss": 50,
                "maximum_consecutive_losses": 2,
                "maximum_symbol_exposure": 500,
                "minimum_minutes_to_close": 15,
                "block_duplicate_symbol_buy": True,
                "live_write_enabled": False,
            }
            policy.update(policy_overrides)
            policy_path = root / "policy.json"
            policy_path.write_text(json.dumps(policy), encoding="utf-8")

            payload = {
                "candidate": {
                    "symbol": "AAPL",
                    "side": "BUY",
                    "confidence": 0.91,
                    "consensus_score": 0.88,
                    "reward_risk": 2.0,
                    "quantity": 0.2,
                    "reference_price": 300,
                },
                "account": {
                    "status": "ACTIVE",
                    "trading_blocked": False,
                    "buying_power": 10000,
                },
                "risk": {
                    "daily_orders": 0,
                    "daily_pnl": 0,
                    "consecutive_losses": 0,
                    "emergency_stop_engaged": False,
                },
                "market": {
                    "market_open": True,
                    "minutes_to_close": 120,
                    "volatility_risk": 0.4,
                    "market_regime_fit": 0.8,
                },
                "positions": [],
            }
            for section, values in overrides.items():
                if section == "positions":
                    payload[section] = values
                else:
                    payload[section].update(values)

            return SmartSafeTradingGuard(root).evaluate(
                policy_path=policy_path,
                candidate=payload["candidate"],
                account=payload["account"],
                risk=payload["risk"],
                market=payload["market"],
                positions=payload["positions"],
                decision_path=root / "decision.json",
                ledger_path=root / "ledger.jsonl",
            )

    def test_good_candidate_shadow_allows(self):
        result = self.evaluate()
        self.assertEqual(result["action"], "SHADOW_ALLOW")
        self.assertTrue(result["would_allow_order"])

    def test_low_confidence_blocks(self):
        result = self.evaluate({
            "candidate": {"confidence": 0.2}
        })
        self.assertEqual(result["action"], "SHADOW_BLOCK")
        self.assertIn(
            "CONFIDENCE_TOO_LOW",
            [item["code"] for item in result["issues"]],
        )

    def test_daily_loss_blocks(self):
        result = self.evaluate({
            "risk": {"daily_pnl": -60}
        })
        self.assertFalse(result["would_allow_order"])

    def test_duplicate_symbol_buy_blocks(self):
        result = self.evaluate({
            "positions": [{"symbol": "AAPL", "market_value": 100}]
        })
        codes = [item["code"] for item in result["issues"]]
        self.assertIn("DUPLICATE_SYMBOL_BUY", codes)

    def test_live_write_policy_blocks(self):
        result = self.evaluate(policy_overrides={
            "live_write_enabled": True
        })
        codes = [item["code"] for item in result["issues"]]
        self.assertIn("LIVE_WRITE_MUST_REMAIN_OFF", codes)

    def test_notional_limit_blocks(self):
        result = self.evaluate({
            "candidate": {"quantity": 1, "reference_price": 300}
        })
        self.assertFalse(result["would_allow_order"])

    def test_quality_score_range(self):
        result = self.evaluate()
        self.assertGreaterEqual(result["quality_score"], 0)
        self.assertLessEqual(result["quality_score"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
