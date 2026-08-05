from __future__ import annotations
import inspect
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from approval_submission_safety.io import write_json
from approval_submission_safety.service import (
    ApprovalSubmissionSafetyService,
)
from approval_submission_safety.token import create_token


class Tests(unittest.TestCase):
    def setup_inputs(self, root: Path, market_open=True):
        ticket = {
            "ticket_id": "ticket-1",
            "idempotency_key": "idem-1",
            "status": "VALID",
            "paper_endpoint_only": True,
            "submission_enabled": False,
            "broker_write_allowed": False,
            "payload": {
                "symbol": "SPY",
                "side": "buy",
                "type": "limit",
                "time_in_force": "day",
                "notional": "100",
                "limit_price": "500",
                "client_order_id": "client-1",
                "submission_enabled": False,
                "broker_write_allowed": False,
            },
        }
        bundle = root / "bundle.json"
        write_json(
            bundle,
            {
                "ticket_bundle_fingerprint": "bundle-1",
                "valid_tickets": [ticket],
            },
        )

        scope = {
            "environment": "paper",
            "operation": "paper_order_submission_review",
            "ticket_id": "ticket-1",
            "idempotency_key": "idem-1",
            "request_fingerprint": "idem-1",
        }
        token = root / "token.json"
        write_json(
            token,
            create_token(scope, "secret", ttl_seconds=300),
        )

        policy = root / "policy.json"
        write_json(
            policy,
            {
                "mode": "paper",
                "paper_endpoint": "https://paper-api.alpaca.markets",
                "symbol_allow_list": ["SPY", "QQQ", "IWM"],
                "max_notional_per_ticket": "500",
                "allowed_risk_levels": ["NORMAL"],
                "require_market_open": True,
                "submission_enabled": False,
                "broker_write_enabled": False,
            },
        )

        market = root / "market.json"
        write_json(
            market,
            {
                "symbols": {
                    "SPY": {"is_open": market_open}
                }
            },
        )
        risk = root / "risk.json"
        write_json(risk, {"risk_level": "NORMAL"})
        nonce = root / "nonce.json"
        write_json(nonce, {"consumed_nonces": []})
        idem = root / "idem.json"
        write_json(idem, {"idempotency_keys": []})
        return bundle, token, policy, market, risk, nonce, idem

    def evaluate(self, root: Path, market_open=True):
        paths = self.setup_inputs(root, market_open)
        return ApprovalSubmissionSafetyService().evaluate(
            ticket_bundle_path=paths[0],
            token_path=paths[1],
            policy_path=paths[2],
            market_path=paths[3],
            risk_path=paths[4],
            nonce_registry_path=paths[5],
            idempotency_registry_path=paths[6],
            output_dir=root / "out",
            secret="secret",
            now=datetime.now(timezone.utc),
        )

    def test_approved_for_separate_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory))
            self.assertEqual(
                result["approved_for_separate_submission_count"], 1
            )

    def test_market_closed_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(
                Path(directory), market_open=False
            )
            self.assertEqual(
                result["approved_for_separate_submission_count"], 0
            )

    def test_broker_request_is_json_only(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory))
            request = result["approved_queue"][0]["broker_request"]
            self.assertFalse(request["network_call_performed"])
            self.assertFalse(request["broker_write_performed"])

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.evaluate(root)
            self.assertTrue(
                (root / "out/submission_safety_dashboard.json").exists()
            )
            self.assertTrue(
                (root / "out/submission_decision_ledger.jsonl").exists()
            )

    def test_zero_orders_contract(self):
        source = inspect.getsource(
            ApprovalSubmissionSafetyService
        )
        self.assertIn('"actual_broker_write_performed": False', source)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
        self.assertIn('"actual_live_orders_submitted": 0', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
