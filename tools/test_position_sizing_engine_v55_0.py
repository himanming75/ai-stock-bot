import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from tools.position_sizing_engine_v55_0 import (
    AccountState,
    PositionSizingConfig,
    PositionSizingEngine,
    PositionSizingRequest,
    load_payload,
)


def account():
    return AccountState(
        equity="100000",
        cash="50000",
        buying_power="50000",
        current_gross_exposure="20000",
        source_sha256="a" * 64,
    )


def config(**overrides):
    data = dict(
        allow_fractional_shares=False,
        lot_size="1",
        min_order_notional="100",
        max_order_notional="25000",
        max_position_percent="0.20",
        max_portfolio_exposure_percent="0.80",
        reserve_cash_percent="0.10",
    )
    data.update(overrides)
    return PositionSizingConfig(**data)


def request(method="fixed_dollar", **overrides):
    data = dict(
        request_id="req-1",
        symbol="AAPL",
        action="BUY",
        entry_price="200",
        method=method,
        signal_sha256="b" * 64,
        fixed_shares=None,
        fixed_dollar="10000",
        percent_of_equity=None,
        risk_percent=None,
        stop_price=None,
        atr=None,
        atr_multiple=None,
        win_rate=None,
        payoff_ratio=None,
        kelly_fraction_cap=None,
        metadata={},
    )
    data.update(overrides)
    return PositionSizingRequest(**data)


class PositionSizingV550Tests(unittest.TestCase):
    def engine(self):
        return PositionSizingEngine(mode="paper")

    def test_fixed_dollar_pass(self):
        r = self.engine().size(account(), request(), config())
        self.assertEqual("PASS", r.status)

    def test_fixed_dollar_shares(self):
        r = self.engine().size(account(), request(), config())
        self.assertEqual("50.000000", r.shares)

    def test_fixed_dollar_notional(self):
        r = self.engine().size(account(), request(), config())
        self.assertEqual("10000.00", r.position_notional)

    def test_fixed_shares(self):
        r = self.engine().size(account(), request("fixed_shares", fixed_shares="25"), config())
        self.assertEqual("25.000000", r.shares)

    def test_fixed_percent_equity(self):
        r = self.engine().size(account(), request("fixed_percent_equity", percent_of_equity="0.10"), config())
        self.assertEqual("10000.00", r.position_notional)

    def test_fixed_risk(self):
        r = self.engine().size(
            account(),
            request("fixed_risk", risk_percent="0.01", stop_price="190"),
            config(),
        )
        self.assertEqual("100.000000", r.shares)
        self.assertEqual("1000.00", r.estimated_risk_amount)

    def test_atr_risk(self):
        r = self.engine().size(
            account(),
            request("atr_risk", risk_percent="0.01", atr="5", atr_multiple="2"),
            config(),
        )
        self.assertEqual("100.000000", r.shares)

    def test_kelly(self):
        r = self.engine().size(
            account(),
            request(
                "kelly_fraction",
                win_rate="0.60",
                payoff_ratio="2",
                kelly_fraction_cap="0.20",
            ),
            config(),
        )
        self.assertEqual("20000.00", r.position_notional)

    def test_hold_rejected(self):
        r = self.engine().size(account(), request(action="HOLD"), config())
        self.assertEqual("FAIL", r.status)

    def test_invalid_action(self):
        r = self.engine().size(account(), request(action="WAIT"), config())
        self.assertIn("invalid_action", r.rejection_reasons)

    def test_empty_request_id(self):
        r = self.engine().size(account(), request(request_id=""), config())
        self.assertIn("request_id_required", r.rejection_reasons)

    def test_empty_symbol(self):
        r = self.engine().size(account(), request(symbol=""), config())
        self.assertIn("symbol_required", r.rejection_reasons)

    def test_symbol_uppercase(self):
        r = self.engine().size(account(), request(symbol="aapl"), config())
        self.assertEqual("AAPL", r.symbol)

    def test_bad_signal_hash(self):
        r = self.engine().size(account(), request(signal_sha256="x"), config())
        self.assertIn("signal_sha256_invalid", r.rejection_reasons)

    def test_bad_entry(self):
        r = self.engine().size(account(), request(entry_price="0"), config())
        self.assertIn("entry_price_must_be_positive", r.rejection_reasons)

    def test_invalid_method(self):
        r = self.engine().size(account(), request(method="bad"), config())
        self.assertIn("invalid_sizing_method", r.rejection_reasons)

    def test_max_order_cap(self):
        r = self.engine().size(account(), request(fixed_dollar="50000"), config())
        self.assertIn("max_order_notional", r.limiting_factors)

    def test_max_position_cap(self):
        r = self.engine().size(
            account(),
            request(fixed_dollar="50000"),
            config(max_order_notional="100000", max_position_percent="0.10"),
        )
        self.assertEqual("10000.00", r.position_notional)

    def test_available_capital_cap(self):
        a = AccountState(**{**asdict(account()), "cash": "5000", "buying_power": "5000"})
        r = self.engine().size(a, request(fixed_dollar="10000"), config(reserve_cash_percent="0"))
        self.assertEqual("5000.00", r.position_notional)

    def test_portfolio_exposure_cap(self):
        a = AccountState(**{**asdict(account()), "current_gross_exposure": "79000"})
        r = self.engine().size(
            a,
            request(fixed_dollar="10000"),
            config(max_order_notional="100000"),
        )
        self.assertEqual("1000.00", r.position_notional)

    def test_min_order_reject(self):
        r = self.engine().size(account(), request(fixed_dollar="50"), config())
        self.assertIn("below_min_order_notional", r.rejection_reasons)

    def test_fractional_disabled(self):
        r = self.engine().size(account(), request(fixed_dollar="1050"), config())
        self.assertEqual("5.000000", r.shares)

    def test_fractional_enabled(self):
        r = self.engine().size(
            account(),
            request(fixed_dollar="1050"),
            config(allow_fractional_shares=True, lot_size="0.001"),
        )
        self.assertEqual("5.250000", r.shares)

    def test_lot_size(self):
        r = self.engine().size(
            account(),
            request(fixed_dollar="1500"),
            config(lot_size="10"),
        )
        self.assertEqual("0.000000", r.shares)

    def test_bad_account_equity(self):
        a = AccountState(**{**asdict(account()), "equity": "0"})
        with self.assertRaises(ValueError):
            self.engine().size(a, request(), config())

    def test_bad_account_hash(self):
        a = AccountState(**{**asdict(account()), "source_sha256": "x"})
        with self.assertRaises(ValueError):
            self.engine().size(a, request(), config())

    def test_negative_cash(self):
        a = AccountState(**{**asdict(account()), "cash": "-1"})
        with self.assertRaises(ValueError):
            self.engine().size(a, request(), config())

    def test_bad_lot(self):
        with self.assertRaises(ValueError):
            self.engine().size(account(), request(), config(lot_size="0"))

    def test_bad_min_max(self):
        with self.assertRaises(ValueError):
            self.engine().size(account(), request(), config(min_order_notional="500", max_order_notional="100"))

    def test_bad_position_percent(self):
        with self.assertRaises(ValueError):
            self.engine().size(account(), request(), config(max_position_percent="1.1"))

    def test_bad_portfolio_percent(self):
        with self.assertRaises(ValueError):
            self.engine().size(account(), request(), config(max_portfolio_exposure_percent="1.1"))

    def test_bad_reserve_percent(self):
        with self.assertRaises(ValueError):
            self.engine().size(account(), request(), config(reserve_cash_percent="1.1"))

    def test_fixed_shares_missing(self):
        r = self.engine().size(account(), request("fixed_shares", fixed_shares=None), config())
        self.assertEqual("FAIL", r.status)

    def test_fixed_dollar_zero(self):
        r = self.engine().size(account(), request(fixed_dollar="0"), config())
        self.assertEqual("FAIL", r.status)

    def test_percent_invalid(self):
        r = self.engine().size(account(), request("fixed_percent_equity", percent_of_equity="2"), config())
        self.assertEqual("FAIL", r.status)

    def test_risk_percent_invalid(self):
        r = self.engine().size(account(), request("fixed_risk", risk_percent="0", stop_price="190"), config())
        self.assertEqual("FAIL", r.status)

    def test_stop_same_as_entry(self):
        r = self.engine().size(account(), request("fixed_risk", risk_percent="0.01", stop_price="200"), config())
        self.assertEqual("FAIL", r.status)

    def test_atr_invalid(self):
        r = self.engine().size(account(), request("atr_risk", risk_percent="0.01", atr="0", atr_multiple="2"), config())
        self.assertEqual("FAIL", r.status)

    def test_atr_multiple_invalid(self):
        r = self.engine().size(account(), request("atr_risk", risk_percent="0.01", atr="5", atr_multiple="0"), config())
        self.assertEqual("FAIL", r.status)

    def test_kelly_negative_becomes_zero(self):
        r = self.engine().size(
            account(),
            request("kelly_fraction", win_rate="0.20", payoff_ratio="1", kelly_fraction_cap="0.20"),
            config(),
        )
        self.assertEqual("FAIL", r.status)

    def test_kelly_bad_win_rate(self):
        r = self.engine().size(
            account(),
            request("kelly_fraction", win_rate="2", payoff_ratio="1", kelly_fraction_cap="0.20"),
            config(),
        )
        self.assertEqual("FAIL", r.status)

    def test_kelly_bad_payoff(self):
        r = self.engine().size(
            account(),
            request("kelly_fraction", win_rate="0.6", payoff_ratio="0", kelly_fraction_cap="0.20"),
            config(),
        )
        self.assertEqual("FAIL", r.status)

    def test_kelly_bad_cap(self):
        r = self.engine().size(
            account(),
            request("kelly_fraction", win_rate="0.6", payoff_ratio="2", kelly_fraction_cap="2"),
            config(),
        )
        self.assertEqual("FAIL", r.status)

    def test_request_hash(self):
        r = self.engine().size(account(), request(), config())
        self.assertEqual(64, len(r.request_sha256))

    def test_sizing_hash(self):
        r = self.engine().size(account(), request(), config())
        self.assertEqual(64, len(r.sizing_sha256))

    def test_network_false(self):
        r = self.engine().size(account(), request(), config())
        self.assertFalse(r.network_used)

    def test_ledger_genesis(self):
        r = self.engine().size(account(), request(), config())
        self.assertEqual("GENESIS", r.ledger[0]["previous_entry_sha256"])

    def test_ledger_chain(self):
        e = self.engine()
        e.size(account(), request(request_id="1"), config())
        r = e.size(account(), request(request_id="2"), config())
        self.assertEqual(r.ledger[0]["entry_sha256"], r.ledger[1]["previous_entry_sha256"])

    def test_deterministic_hash(self):
        a = self.engine().size(account(), request(), config())
        b = self.engine().size(account(), request(), config())
        self.assertEqual(a.sizing_sha256, b.sizing_sha256)

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            PositionSizingEngine(mode="bad")

    def test_live_blocked(self):
        with self.assertRaises(PermissionError):
            PositionSizingEngine(mode="live").size(account(), request(), config())

    def test_live_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            PositionSizingEngine(mode="live", enable_live=True).size(account(), request(), config())

    def test_export(self):
        e = self.engine()
        r = e.size(account(), request(), config())
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "out.json"
            e.export(p, r)
            payload = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual("PASS", payload["result"]["status"])

    def test_load_payload(self):
        payload = {"account": asdict(account()), "request": asdict(request()), "config": asdict(config())}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "in.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            a, r, c = load_payload(p)
            self.assertEqual("100000", a.equity)
            self.assertEqual("req-1", r.request_id)
            self.assertFalse(c.allow_fractional_shares)


if __name__ == "__main__":
    unittest.main()
