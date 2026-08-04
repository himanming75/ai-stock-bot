from __future__ import annotations
import unittest
from paper_order_proposal.engine import build_proposal
from paper_order_proposal.replay import verify


def policy():
    return {
        "paper_endpoint_only": True,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "maximum_new_orders_per_day": 0,
        "maximum_proposal_notional": 1000,
        "daily_loss_limit": 500,
        "approval_token_ttl_seconds": 300,
    }


def decision():
    return {
        "state": "GOVERNED_DECISION_CANDIDATE_READY",
        "status": "PASS",
        "decision_hash": "a" * 64,
        "paper_order_candidate": {
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 2,
            "order_type": "market",
            "time_in_force": "day",
            "confidence": 0.9,
            "decision_allowed": True,
            "submission_allowed": False,
        },
    }


def runtime():
    return {
        "reference_price": 200,
        "market_open": True,
        "kill_switch_active": False,
        "account_status": "ACTIVE",
        "trading_blocked": False,
        "buying_power": 100000,
        "position_qty": 0,
        "daily_pnl": 0,
        "open_orders": [],
    }


class Tests(unittest.TestCase):
    def test_awaiting_approval(self):
        result = build_proposal(decision(), runtime(), policy())
        self.assertEqual(result["state"], "PAPER_ORDER_PROPOSAL_AWAITING_APPROVAL")

    def test_market_closed_blocks(self):
        value = runtime()
        value["market_open"] = False
        result = build_proposal(decision(), value, policy())
        self.assertIn("MARKET_CLOSED", result["checks"]["blocking_reasons"])

    def test_kill_switch_blocks(self):
        value = runtime()
        value["kill_switch_active"] = True
        result = build_proposal(decision(), value, policy())
        self.assertIn("KILL_SWITCH_ACTIVE", result["checks"]["blocking_reasons"])

    def test_duplicate_blocks(self):
        value = runtime()
        value["open_orders"] = [{"symbol": "AAPL", "side": "buy", "status": "accepted"}]
        result = build_proposal(decision(), value, policy())
        self.assertIn("DUPLICATE_OPEN_ORDER", result["checks"]["blocking_reasons"])

    def test_daily_loss_blocks(self):
        value = runtime()
        value["daily_pnl"] = -600
        result = build_proposal(decision(), value, policy())
        self.assertIn("DAILY_LOSS_LIMIT_REACHED", result["checks"]["blocking_reasons"])

    def test_notional_cap_blocks(self):
        value = runtime()
        value["reference_price"] = 600
        result = build_proposal(decision(), value, policy())
        self.assertIn("MAXIMUM_PROPOSAL_NOTIONAL_EXCEEDED", result["checks"]["blocking_reasons"])

    def test_replay_valid(self):
        result = build_proposal(decision(), runtime(), policy())
        self.assertTrue(verify(result)["valid"])

    def test_zero_orders(self):
        result = build_proposal(decision(), runtime(), policy())
        self.assertFalse(result["proposal"]["submission_allowed"])
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
