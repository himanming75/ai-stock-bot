from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from autonomous_paper_runtime.shadow_decision_bootstrap import (
    ShadowDecisionBootstrap,
)


class Tests(unittest.TestCase):
    def write(self, path: Path, payload: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def data(self):
        scheduled = {
            "status": "PASS",
            "state": "WINDOWS_SCHEDULED_READ_ONLY_PLAN_READY",
            "windows_scheduled_collection_ready": True,
            "schedule_id": "schedule-001",
            "pilot_id": "pilot-001",
            "safe_mode_engaged": False,
        }
        policy = {
            "shadow_session_id": "shadow-session-001",
            "shadow_mode": True,
            "order_submission_enabled": False,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "max_shadow_notional": 1000,
            "max_shadow_quantity": 10,
            "minimum_confidence": 0.70,
            "allowed_actions": ["BUY", "SELL", "HOLD"],
        }
        signal = {
            "symbol": "AAPL",
            "action": "BUY",
            "confidence": 0.85,
            "reference_price": 100,
            "quantity": 2,
            "as_of": "2026-08-02T06:30:00Z",
        }
        portfolio = {
            "account": {
                "status": "ACTIVE",
                "account_blocked": False,
                "trading_blocked": False,
            },
            "positions": [],
            "open_orders": [],
        }
        return scheduled, policy, signal, portfolio

    def run_case(self, values, preexisting_ledger=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        names = ["scheduled", "policy", "signal", "portfolio"]
        paths = {name: root/f"{name}.json" for name in names}

        for name, value in zip(names, values):
            if value is not None:
                self.write(paths[name], value)

        ledger = root/"ledger.jsonl"
        if preexisting_ledger:
            ledger.write_text(
                json.dumps(preexisting_ledger) + "\n",
                encoding="utf-8",
            )

        result = ShadowDecisionBootstrap().run(
            scheduled_result_path=paths["scheduled"],
            shadow_policy_path=paths["policy"],
            signal_snapshot_path=paths["signal"],
            portfolio_snapshot_path=paths["portfolio"],
            shadow_decision_path=root/"decision.json",
            risk_report_path=root/"risk.json",
            shadow_ledger_path=ledger,
            shadow_token_path=root/"token.json",
            result_path=root/"result.json",
        )
        return result, root

    def test_wait_before_schedule_ready(self):
        scheduled, policy, signal, portfolio = self.data()
        scheduled = {
            "status": "PASS",
            "state": "WAIT_AUTOMATIC_SNAPSHOT_COLLECTOR",
            "windows_scheduled_collection_ready": False,
            "safe_mode_engaged": False,
        }
        result, _ = self.run_case(
            (scheduled, policy, signal, portfolio)
        )
        self.assertEqual(
            result["state"],
            "WAIT_WINDOWS_SCHEDULED_COLLECTION",
        )

    def test_buy_shadow_decision_ready(self):
        result, root = self.run_case(self.data())
        self.assertEqual(result["state"], "SHADOW_DECISION_READY")
        self.assertEqual(result["approved_action"], "BUY")
        self.assertEqual(result["approved_quantity"], 2)
        self.assertTrue((root/"ledger.jsonl").exists())
        self.assertTrue((root/"token.json").exists())

    def test_low_confidence_becomes_hold(self):
        scheduled, policy, signal, portfolio = self.data()
        signal = dict(signal)
        signal["confidence"] = 0.50
        result, _ = self.run_case(
            (scheduled, policy, signal, portfolio)
        )
        self.assertEqual(result["state"], "SHADOW_DECISION_READY")
        self.assertFalse(result["risk_approved"])
        self.assertEqual(result["approved_action"], "HOLD")

    def test_notional_limit_becomes_hold(self):
        scheduled, policy, signal, portfolio = self.data()
        signal = dict(signal)
        signal["reference_price"] = 1000
        signal["quantity"] = 2
        result, _ = self.run_case(
            (scheduled, policy, signal, portfolio)
        )
        self.assertEqual(result["state"], "SHADOW_DECISION_READY")
        self.assertFalse(result["risk_approved"])
        self.assertIn(
            "SHADOW_NOTIONAL_LIMIT_EXCEEDED",
            result["risk_reasons"],
        )

    def test_existing_position_becomes_hold(self):
        scheduled, policy, signal, portfolio = self.data()
        portfolio = dict(portfolio)
        portfolio["positions"] = [{"symbol": "AAPL", "qty": "1"}]
        result, _ = self.run_case(
            (scheduled, policy, signal, portfolio)
        )
        self.assertFalse(result["risk_approved"])
        self.assertIn(
            "EXISTING_POSITION_PRESENT",
            result["risk_reasons"],
        )

    def test_order_submission_policy_blocks(self):
        scheduled, policy, signal, portfolio = self.data()
        policy = dict(policy)
        policy["order_submission_enabled"] = True
        result, _ = self.run_case(
            (scheduled, policy, signal, portfolio)
        )
        self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
