import json
import tempfile
import unittest
from pathlib import Path

from autonomous_paper_runtime.controlled_paper_order_preparation import (
    APPROVAL_PHRASE,
    LIVE_BASE_URL,
    ControlledPaperOrderPreparation,
)


class Tests(unittest.TestCase):
    def write(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def data(self):
        dashboard = {
            "dashboard_state": "READY",
            "read_only": True,
            "order_submission_enabled": False,
            "broker_write_enabled": False,
            "runtime": {"safe_mode": False},
        }
        policy = {
            "preparation_id": "paper-prep-001",
            "paper_only": True,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "network_write_enabled": False,
            "maximum_order_notional": 100,
            "maximum_order_quantity": 5,
            "maximum_daily_candidates": 1,
            "manual_approval_required": True,
            "expected_base_url": (
                "https://paper-api.alpaca.markets"
            ),
        }
        candidate = {
            "signal_id": "shadow-signal-001",
            "symbol": "AAPL",
            "side": "buy",
            "order_type": "market",
            "time_in_force": "day",
            "quantity": 1,
            "reference_price": 50,
            "shadow_approved": True,
            "daily_candidate_number": 1,
            "duplicate_candidate": False,
            "market_closed": False,
            "emergency_stop_engaged": False,
        }
        account = {
            "account": {
                "status": "ACTIVE",
                "account_blocked": False,
                "trading_blocked": False,
                "buying_power": "100000",
            }
        }
        return dashboard, policy, candidate, account

    def run_case(
        self,
        values,
        approval_phrase="",
        base_url="https://paper-api.alpaca.markets",
    ):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        names = ["dashboard", "policy", "candidate", "account"]
        paths = {name: root/f"{name}.json" for name in names}

        for name, value in zip(names, values):
            if value is not None:
                self.write(paths[name], value)

        result = ControlledPaperOrderPreparation().run(
            dashboard_result_path=paths["dashboard"],
            preparation_policy_path=paths["policy"],
            order_candidate_path=paths["candidate"],
            account_snapshot_path=paths["account"],
            prepared_order_path=root/"prepared.json",
            risk_report_path=root/"risk.json",
            approval_gate_path=root/"approval.json",
            preparation_token_path=root/"token.json",
            result_path=root/"result.json",
            approval_phrase=approval_phrase,
            base_url=base_url,
        )
        return result, root

    def test_preparation_ready_without_submission(self):
        result, root = self.run_case(self.data())
        self.assertEqual(
            result["state"],
            "CONTROLLED_PAPER_ORDER_PREPARATION_READY",
        )
        self.assertFalse(result["manual_approval_ready"])
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertTrue((root/"prepared.json").exists())

    def test_approval_phrase_verified(self):
        result, _ = self.run_case(
            self.data(),
            approval_phrase=APPROVAL_PHRASE,
        )
        self.assertTrue(result["manual_approval_ready"])
        self.assertTrue(result["approval_phrase_verified"])
        self.assertEqual(result["write_requests_executed"], 0)

    def test_live_endpoint_blocks(self):
        result, _ = self.run_case(
            self.data(),
            base_url=LIVE_BASE_URL,
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_notional_limit_holds_preparation(self):
        dashboard, policy, candidate, account = self.data()
        candidate = dict(candidate)
        candidate["quantity"] = 3
        candidate["reference_price"] = 50
        result, _ = self.run_case(
            (dashboard, policy, candidate, account)
        )
        self.assertEqual(result["state"], "WAIT_CONTROLLED_PAPER_INPUT")
        self.assertFalse(result["risk_approved"])
        self.assertIn(
            "NOTIONAL_LIMIT_EXCEEDED",
            result["risk_reasons"],
        )

    def test_submission_policy_blocks(self):
        dashboard, policy, candidate, account = self.data()
        policy = dict(policy)
        policy["order_submission_enabled"] = True
        result, _ = self.run_case(
            (dashboard, policy, candidate, account)
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_blocked_account_blocks(self):
        dashboard, policy, candidate, account = self.data()
        account = json.loads(json.dumps(account))
        account["account"]["account_blocked"] = True
        result, _ = self.run_case(
            (dashboard, policy, candidate, account)
        )
        self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
