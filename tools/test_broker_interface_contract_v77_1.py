from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from broker.contracts_v77_1 import (
    BrokerContractError,
    BrokerOrderRequest,
    BrokerSafetyPolicy,
    OrderSide,
    OrderType,
    TimeInForce,
)
from tools.broker_interface_contract_v77_1 import (
    digest,
    validate_config,
    verify_contract,
    write_outputs,
)
from tools.verify_broker_interface_contract_v77_1 import verify_output


class V771Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "contract_scope": "BROKER_INTERFACE_CONTRACT",
            "expected_framework_commit_sha": "a" * 7,
            "expected_v76_24_closure_sha256": "b" * 64,
            "expected_v76_24_closure_chain_sha256": "c" * 64,
            "required_environment": "offline",
            "network_allowed": False,
            "broker_connection_allowed": False,
            "order_submission_allowed": False,
            "live_trading_allowed": False,
            "live_approval_allowed": False,
            "require_runtime_protocol": True,
            "require_immutable_contract_models": True,
            "require_decimal_financial_fields": True,
            "require_terminal_status_definition": True,
            "require_source_anchor_match": True,
        }

    def test_config(self) -> None:
        validate_config(self.config)

    def test_valid_limit_request(self) -> None:
        request = BrokerOrderRequest(
            client_order_id="strategy-1-0001",
            symbol="aapl",
            side=OrderSide.BUY,
            quantity=Decimal("2"),
            order_type=OrderType.LIMIT,
            time_in_force=TimeInForce.DAY,
            limit_price=Decimal("190.25"),
        )
        request.validate(BrokerSafetyPolicy())

    def test_market_order_rejects_limit_price(self) -> None:
        request = BrokerOrderRequest(
            client_order_id="strategy-1-0002",
            symbol="MSFT",
            side=OrderSide.BUY,
            quantity=Decimal("1"),
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            limit_price=Decimal("400"),
        )
        with self.assertRaises(BrokerContractError):
            request.validate(BrokerSafetyPolicy())

    def test_live_policy_rejected(self) -> None:
        from broker.contracts_v77_1 import BrokerEnvironment

        with self.assertRaises(BrokerContractError):
            BrokerSafetyPolicy(environment=BrokerEnvironment.LIVE).validate()

    def test_pass_and_independent_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "release/v77_1/output"
            closure_dir = root / "release/v76_24/output"
            closure_dir.mkdir(parents=True)

            closure = {
                "status": "PASS",
                "project_release_closed": True,
                "offline_paper_release_complete": True,
                "closure_sha256": "b" * 64,
                "closure_chain_sha256": "c" * 64,
            }
            summary = {
                "closure_sha256": "b" * 64,
                "closure_chain_sha256": "c" * 64,
            }
            (closure_dir / "project_release_closure_v76_24.json").write_text(
                json.dumps(closure), encoding="utf-8"
            )
            (closure_dir / "project_release_closure_summary_v76_24.json").write_text(
                json.dumps(summary), encoding="utf-8"
            )
            git = {
                "head_sha": "a" * 40,
                "head_short_sha": "a" * 7,
                "origin_main_sha": "a" * 40,
                "branch": "main",
                "tracked_status_short": [],
            }
            with patch(
                "tools.broker_interface_contract_v77_1.git_state", return_value=git
            ):
                result = verify_contract(root, self.config)
            self.assertEqual(result["status"], "PASS")
            write_outputs(result, output)
            self.assertTrue(verify_output(output)["verified"])

    def test_digest_deterministic(self) -> None:
        self.assertEqual(digest({"b": 2, "a": 1}), digest({"a": 1, "b": 2}))


if __name__ == "__main__":
    unittest.main()
