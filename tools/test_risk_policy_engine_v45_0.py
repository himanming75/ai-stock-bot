from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.risk_policy_engine_v45_0 import (
    AccountRiskState,
    OrderValidationInput,
    RiskPolicyConfig,
    RiskPolicyEngine,
    canonical_hash,
)


NOW = "2026-07-29T17:00:00+00:00"


def make_validation(**overrides) -> OrderValidationInput:
    core = {
        "schema_version": "v44.0.order_validation.1",
        "version": "44.0",
        "status": "PASS",
        "symbol": "AAPL",
        "client_order_id": "v43-order-001",
        "side": "buy",
        "quantity": "10",
        "reference_price": "200",
        "order_notional": "2000",
        "checks": [{"check_id": "demo", "status": "PASS", "message": "ok"}],
        "rejection_reasons": [],
        "network_used": False,
    }
    core.update(overrides)
    payload = dict(core)
    payload["validation_sha256"] = canonical_hash(core)
    return OrderValidationInput(**payload)


def make_account(**overrides) -> AccountRiskState:
    data = {
        "equity": "100000",
        "cash": "50000",
        "gross_exposure": "30000",
        "symbol_exposure": "10000",
        "open_positions": 3,
        "symbol_already_open": False,
        "daily_realized_pnl": "-500",
        "consecutive_losses": 1,
        "daily_trade_count": 5,
        "last_loss_at": "2026-07-29T16:30:00+00:00",
        "peak_equity": "105000",
        "current_equity": "100000",
    }
    data.update(overrides)
    return AccountRiskState(**data)


class RiskPolicyEngineV450Tests(unittest.TestCase):
    def engine(self, **kwargs) -> RiskPolicyEngine:
        return RiskPolicyEngine(reference_time=NOW, **kwargs)

    def test_approved_order(self) -> None:
        result = self.engine().evaluate(
            make_validation(),
            make_account(),
            stop_price="195",
        )
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.decision, "approve")

    def test_validation_status_fail(self) -> None:
        result = self.engine().evaluate(
            make_validation(status="FAIL"),
            make_account(),
            stop_price="195",
        )
        self.assertEqual(result.status, "FAIL")

    def test_validation_hash_fail(self) -> None:
        validation = make_validation()
        tampered = OrderValidationInput(
            **{**validation.__dict__, "validation_sha256": "0" * 64}
        )
        result = self.engine().evaluate(
            tampered,
            make_account(),
            stop_price="195",
        )
        self.assertEqual(result.status, "FAIL")

    def test_network_usage_fail(self) -> None:
        result = self.engine().evaluate(
            make_validation(network_used=True),
            make_account(),
            stop_price="195",
        )
        self.assertEqual(result.status, "FAIL")

    def test_risk_amount_limit(self) -> None:
        result = self.engine().evaluate(
            make_validation(),
            make_account(),
            stop_price="50",
        )
        self.assertEqual(result.status, "FAIL")

    def test_risk_percent_limit(self) -> None:
        config = RiskPolicyConfig(
            max_order_risk_amount="100000",
            max_order_risk_pct="0.01",
        )
        result = self.engine(config=config).evaluate(
            make_validation(),
            make_account(),
            stop_price="195",
        )
        self.assertEqual(result.status, "FAIL")

    def test_position_weight_limit(self) -> None:
        result = self.engine().evaluate(
            make_validation(order_notional="15000", quantity="75"),
            make_account(symbol_exposure="10000"),
            stop_price="199",
        )
        self.assertEqual(result.status, "FAIL")

    def test_symbol_exposure_limit(self) -> None:
        config = RiskPolicyConfig(
            max_position_weight_pct="100",
            max_symbol_exposure_pct="15",
        )
        result = self.engine(config=config).evaluate(
            make_validation(order_notional="10000", quantity="50"),
            make_account(symbol_exposure="10000"),
            stop_price="199",
        )
        self.assertEqual(result.status, "FAIL")

    def test_gross_exposure_limit(self) -> None:
        result = self.engine().evaluate(
            make_validation(order_notional="20000", quantity="100"),
            make_account(gross_exposure="90000", symbol_exposure="0"),
            stop_price="199",
        )
        self.assertEqual(result.status, "FAIL")

    def test_max_open_positions(self) -> None:
        result = self.engine().evaluate(
            make_validation(),
            make_account(open_positions=10),
            stop_price="195",
        )
        self.assertEqual(result.status, "FAIL")

    def test_duplicate_symbol_entry(self) -> None:
        result = self.engine().evaluate(
            make_validation(),
            make_account(symbol_already_open=True),
            stop_price="195",
        )
        self.assertEqual(result.status, "FAIL")

    def test_duplicate_symbol_entry_allowed(self) -> None:
        config = RiskPolicyConfig(allow_duplicate_symbol_entry=True)
        result = self.engine(config=config).evaluate(
            make_validation(),
            make_account(symbol_already_open=True),
            stop_price="195",
        )
        self.assertEqual(result.status, "PASS")

    def test_daily_loss_limit(self) -> None:
        result = self.engine().evaluate(
            make_validation(),
            make_account(daily_realized_pnl="-2000"),
            stop_price="195",
        )
        self.assertEqual(result.status, "FAIL")

    def test_consecutive_loss_limit(self) -> None:
        result = self.engine().evaluate(
            make_validation(),
            make_account(consecutive_losses=3),
            stop_price="195",
        )
        self.assertEqual(result.status, "FAIL")

    def test_daily_trade_count_limit(self) -> None:
        result = self.engine().evaluate(
            make_validation(),
            make_account(daily_trade_count=20),
            stop_price="195",
        )
        self.assertEqual(result.status, "FAIL")

    def test_loss_cooldown(self) -> None:
        result = self.engine().evaluate(
            make_validation(),
            make_account(last_loss_at="2026-07-29T16:55:00+00:00"),
            stop_price="195",
        )
        self.assertEqual(result.status, "FAIL")

    def test_drawdown_limit(self) -> None:
        result = self.engine().evaluate(
            make_validation(),
            make_account(peak_equity="120000", current_equity="100000"),
            stop_price="195",
        )
        self.assertEqual(result.status, "FAIL")

    def test_cash_reserve_limit(self) -> None:
        result = self.engine().evaluate(
            make_validation(order_notional="45000", quantity="225"),
            make_account(cash="50000", symbol_exposure="0", gross_exposure="0"),
            stop_price="199",
        )
        self.assertEqual(result.status, "FAIL")

    def test_sell_reduces_exposure(self) -> None:
        result = self.engine().evaluate(
            make_validation(side="sell"),
            make_account(symbol_already_open=True),
            stop_price="205",
        )
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.projected_symbol_exposure_pct, "8")

    def test_decision_hash_present(self) -> None:
        result = self.engine().evaluate(
            make_validation(),
            make_account(),
            stop_price="195",
        )
        self.assertEqual(len(result.decision_sha256), 64)

    def test_network_false(self) -> None:
        result = self.engine().evaluate(
            make_validation(),
            make_account(),
            stop_price="195",
        )
        self.assertFalse(result.network_used)

    def test_live_gate(self) -> None:
        with self.assertRaises(PermissionError):
            self.engine(mode="live").evaluate(
                make_validation(),
                make_account(),
                stop_price="195",
            )

    def test_live_transport_not_implemented(self) -> None:
        with self.assertRaises(NotImplementedError):
            self.engine(mode="live", enable_live=True).evaluate(
                make_validation(),
                make_account(),
                stop_price="195",
            )

    def test_export(self) -> None:
        result = self.engine().evaluate(
            make_validation(),
            make_account(),
            stop_price="195",
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "result.json"
            RiskPolicyEngine.export(path, result)
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["decision"]["status"], "PASS")
        self.assertFalse(payload["network_used"])


if __name__ == "__main__":
    unittest.main()
