from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.order_validator_v44_0 import (
    OrderIntentInput,
    OrderValidator,
    ValidationConfig,
    canonical_hash,
)


NOW = "2026-07-29T17:00:00+00:00"


def make_intent(**overrides) -> OrderIntentInput:
    core = {
        "schema_version": "v43.0.order_intent.1",
        "version": "43.0",
        "status": "ACCEPTED",
        "symbol": "AAPL",
        "signal_decision": "BUY",
        "side": "buy",
        "quantity": "10",
        "order_type": "market",
        "time_in_force": "day",
        "limit_price": None,
        "confidence": 90,
        "generated_at": NOW,
        "expires_at": "2026-07-29T17:05:00+00:00",
        "client_order_id": "v43-test-order-001",
        "source_signal_sha256": "a" * 64,
        "rejection_reasons": [],
        "network_used": False,
    }
    core.update(overrides)
    payload = dict(core)
    payload["intent_sha256"] = canonical_hash(core)
    return OrderIntentInput(**payload)


class OrderValidatorV440Tests(unittest.TestCase):
    def validator(self, **kwargs) -> OrderValidator:
        return OrderValidator(reference_time=NOW, **kwargs)

    def test_valid_buy_market_order(self) -> None:
        result = self.validator().validate(make_intent(), market_price="200")
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.order_notional, "2000")

    def test_valid_sell_order(self) -> None:
        result = self.validator().validate(
            make_intent(
                signal_decision="SELL",
                side="sell",
                client_order_id="v43-test-order-002",
            ),
            market_price="200",
            position_quantity="10",
        )
        self.assertEqual(result.status, "PASS")

    def test_rejected_intent_fails(self) -> None:
        result = self.validator().validate(
            make_intent(status="REJECTED", client_order_id="v43-test-order-003"),
            market_price="200",
        )
        self.assertEqual(result.status, "FAIL")

    def test_zero_quantity_fails(self) -> None:
        result = self.validator().validate(
            make_intent(quantity="0", client_order_id="v43-test-order-004"),
            market_price="200",
        )
        self.assertEqual(result.status, "FAIL")

    def test_lot_size_fails(self) -> None:
        validator = self.validator(config=ValidationConfig(lot_size="5"))
        result = validator.validate(
            make_intent(quantity="7", client_order_id="v43-test-order-005"),
            market_price="200",
        )
        self.assertEqual(result.status, "FAIL")

    def test_tick_size_fails(self) -> None:
        validator = self.validator(config=ValidationConfig(tick_size="0.05"))
        result = validator.validate(
            make_intent(client_order_id="v43-test-order-006"),
            market_price="200.03",
        )
        self.assertEqual(result.status, "FAIL")

    def test_limit_order_passes(self) -> None:
        result = self.validator().validate(
            make_intent(
                order_type="limit",
                limit_price="199.50",
                client_order_id="v43-test-order-007",
            ),
            market_price="200",
        )
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.reference_price, "199.5")

    def test_limit_order_without_price_fails(self) -> None:
        result = self.validator().validate(
            make_intent(order_type="limit", client_order_id="v43-test-order-008"),
            market_price="200",
        )
        self.assertEqual(result.status, "FAIL")

    def test_market_order_with_limit_price_fails(self) -> None:
        result = self.validator().validate(
            make_intent(limit_price="199", client_order_id="v43-test-order-009"),
            market_price="200",
        )
        self.assertEqual(result.status, "FAIL")

    def test_minimum_notional_fails(self) -> None:
        validator = self.validator(
            config=ValidationConfig(minimum_notional="5000")
        )
        result = validator.validate(
            make_intent(client_order_id="v43-test-order-010"),
            market_price="200",
        )
        self.assertEqual(result.status, "FAIL")

    def test_maximum_notional_fails(self) -> None:
        validator = self.validator(
            config=ValidationConfig(maximum_notional="1000")
        )
        result = validator.validate(
            make_intent(client_order_id="v43-test-order-011"),
            market_price="200",
        )
        self.assertEqual(result.status, "FAIL")

    def test_insufficient_cash_fails(self) -> None:
        result = self.validator().validate(
            make_intent(client_order_id="v43-test-order-012"),
            market_price="200",
            available_cash="100",
        )
        self.assertEqual(result.status, "FAIL")

    def test_insufficient_buying_power_fails(self) -> None:
        result = self.validator().validate(
            make_intent(client_order_id="v43-test-order-013"),
            market_price="200",
            buying_power="100",
        )
        self.assertEqual(result.status, "FAIL")

    def test_insufficient_position_fails(self) -> None:
        result = self.validator().validate(
            make_intent(
                signal_decision="SELL",
                side="sell",
                client_order_id="v43-test-order-014",
            ),
            market_price="200",
            position_quantity="5",
        )
        self.assertEqual(result.status, "FAIL")

    def test_market_closed_fails(self) -> None:
        result = self.validator().validate(
            make_intent(client_order_id="v43-test-order-015"),
            market_price="200",
            market_open=False,
        )
        self.assertEqual(result.status, "FAIL")

    def test_halted_fails(self) -> None:
        result = self.validator().validate(
            make_intent(client_order_id="v43-test-order-016"),
            market_price="200",
            halted=True,
        )
        self.assertEqual(result.status, "FAIL")

    def test_delisted_fails(self) -> None:
        result = self.validator().validate(
            make_intent(client_order_id="v43-test-order-017"),
            market_price="200",
            delisted=True,
        )
        self.assertEqual(result.status, "FAIL")

    def test_expired_intent_fails(self) -> None:
        result = self.validator().validate(
            make_intent(
                expires_at="2026-07-29T16:59:59+00:00",
                client_order_id="v43-test-order-018",
            ),
            market_price="200",
        )
        self.assertEqual(result.status, "FAIL")

    def test_tampered_hash_fails(self) -> None:
        intent = make_intent(client_order_id="v43-test-order-019")
        tampered = OrderIntentInput(
            **{**intent.__dict__, "intent_sha256": "0" * 64}
        )
        result = self.validator().validate(tampered, market_price="200")
        self.assertEqual(result.status, "FAIL")

    def test_duplicate_client_order_id_fails(self) -> None:
        validator = self.validator()
        intent = make_intent(client_order_id="v43-test-order-020")
        first = validator.validate(intent, market_price="200")
        second = validator.validate(intent, market_price="200")
        self.assertEqual(first.status, "PASS")
        self.assertEqual(second.status, "FAIL")

    def test_validation_hash_present(self) -> None:
        result = self.validator().validate(
            make_intent(client_order_id="v43-test-order-021"),
            market_price="200",
        )
        self.assertEqual(len(result.validation_sha256), 64)

    def test_network_false(self) -> None:
        result = self.validator().validate(
            make_intent(client_order_id="v43-test-order-022"),
            market_price="200",
        )
        self.assertFalse(result.network_used)

    def test_live_gate(self) -> None:
        with self.assertRaises(PermissionError):
            self.validator(mode="live").validate(make_intent(), market_price="200")

    def test_live_transport_not_implemented(self) -> None:
        with self.assertRaises(NotImplementedError):
            self.validator(mode="live", enable_live=True).validate(
                make_intent(),
                market_price="200",
            )

    def test_export(self) -> None:
        result = self.validator().validate(
            make_intent(client_order_id="v43-test-order-023"),
            market_price="200",
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "result.json"
            OrderValidator.export(path, result)
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["result"]["status"], "PASS")
        self.assertFalse(payload["network_used"])


if __name__ == "__main__":
    unittest.main()
