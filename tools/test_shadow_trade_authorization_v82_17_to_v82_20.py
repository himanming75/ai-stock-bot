
import json
import tempfile
import unittest
from pathlib import Path

from shadow_runtime.trade_authorization_v82_17_20 import (
    evaluate_authorization,
    run_shadow_trade_authorization,
)


class Tests(unittest.TestCase):
    def policy(self):
        return {
            "shadow_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "allowed_actions": ["BUY", "SELL", "HOLD"],
            "blocked_symbols": [],
            "maximum_quantity": 100,
        }

    def risk_clear(self):
        return {
            "state": "SHADOW_RISK_CLEAR",
            "kill_switch_active": False,
            "recovery_lock_active": False,
        }

    def test_buy_authorized(self):
        result = evaluate_authorization(
            signal={
                "symbol": "AAPL",
                "shadow_action": "BUY",
                "quantity": 1,
            },
            risk_result=self.risk_clear(),
            policy=self.policy(),
            market_session_open=True,
        )
        self.assertTrue(result["authorized"])
        self.assertEqual(result["decision"], "AUTHORIZED")

    def test_hold_no_action(self):
        result = evaluate_authorization(
            signal={
                "symbol": "",
                "shadow_action": "HOLD",
                "quantity": 0,
            },
            risk_result=self.risk_clear(),
            policy=self.policy(),
            market_session_open=False,
        )
        self.assertTrue(result["authorized"])
        self.assertEqual(result["decision"], "NO_ACTION")

    def test_kill_switch_rejected(self):
        risk = self.risk_clear()
        risk["kill_switch_active"] = True
        result = evaluate_authorization(
            signal={
                "symbol": "AAPL",
                "shadow_action": "BUY",
                "quantity": 1,
            },
            risk_result=risk,
            policy=self.policy(),
            market_session_open=True,
        )
        self.assertFalse(result["authorized"])
        self.assertIn(
            "KILL_SWITCH_ACTIVE",
            result["authorization_reasons"],
        )

    def test_recovery_lock_rejected(self):
        risk = self.risk_clear()
        risk["recovery_lock_active"] = True
        result = evaluate_authorization(
            signal={
                "symbol": "AAPL",
                "shadow_action": "BUY",
                "quantity": 1,
            },
            risk_result=risk,
            policy=self.policy(),
            market_session_open=True,
        )
        self.assertIn(
            "RECOVERY_LOCK_ACTIVE",
            result["authorization_reasons"],
        )

    def test_market_closed_rejected(self):
        result = evaluate_authorization(
            signal={
                "symbol": "AAPL",
                "shadow_action": "BUY",
                "quantity": 1,
            },
            risk_result=self.risk_clear(),
            policy=self.policy(),
            market_session_open=False,
        )
        self.assertIn(
            "MARKET_SESSION_CLOSED",
            result["authorization_reasons"],
        )

    def test_symbol_blocked(self):
        policy = self.policy()
        policy["blocked_symbols"] = ["AAPL"]
        result = evaluate_authorization(
            signal={
                "symbol": "AAPL",
                "shadow_action": "BUY",
                "quantity": 1,
            },
            risk_result=self.risk_clear(),
            policy=policy,
            market_session_open=True,
        )
        self.assertIn(
            "SYMBOL_BLOCKED",
            result["authorization_reasons"],
        )

    def test_quantity_limit(self):
        result = evaluate_authorization(
            signal={
                "symbol": "AAPL",
                "shadow_action": "BUY",
                "quantity": 101,
            },
            risk_result=self.risk_clear(),
            policy=self.policy(),
            market_session_open=True,
        )
        self.assertIn(
            "MAXIMUM_QUANTITY_EXCEEDED",
            result["authorization_reasons"],
        )

    def write(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def run_case(self, signal=None, risk=None, market_open=True):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)

        self.write(root / "signal.json", signal or {
            "symbol": "AAPL",
            "shadow_action": "BUY",
            "quantity": 1,
            "observed_at": "2026-08-03T00:00:00+00:00",
        })
        self.write(root / "risk.json", risk or self.risk_clear())
        self.write(root / "policy.json", self.policy())

        result = run_shadow_trade_authorization(
            signal_path=root / "signal.json",
            risk_result_path=root / "risk.json",
            policy_path=root / "policy.json",
            authorization_ledger_path=root / "ledger.jsonl",
            authorization_snapshot_path=root / "snapshot.json",
            dashboard_path=root / "dashboard.json",
            result_path=root / "result.json",
            market_session_open=market_open,
        )
        return result, root

    def test_outputs_written(self):
        result, root = self.run_case()
        self.assertTrue(result["authorization_ledger_written"])
        self.assertTrue((root / "ledger.jsonl").exists())
        self.assertTrue((root / "snapshot.json").exists())
        self.assertTrue((root / "dashboard.json").exists())

    def test_rejected_state(self):
        risk = self.risk_clear()
        risk["state"] = "SHADOW_RISK_KILL_SWITCH_ACTIVE"
        risk["kill_switch_active"] = True
        result, _ = self.run_case(risk=risk)
        self.assertEqual(result["state"], "SHADOW_TRADE_REJECTED")

    def test_read_only_contract(self):
        result, _ = self.run_case()
        self.assertFalse(result["broker_write_enabled"])
        self.assertFalse(result["order_submission_enabled"])
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
