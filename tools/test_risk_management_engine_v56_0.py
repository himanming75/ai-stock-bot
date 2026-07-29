import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from tools.risk_management_engine_v56_0 import (
    RiskConfig,
    RiskManagementEngine,
    RiskRequest,
    RiskState,
    load_payload,
)


def state(**overrides):
    data = dict(
        equity="100000",
        daily_realized_pnl="-500",
        daily_unrealized_pnl="-250",
        consecutive_losses=1,
        open_position_count=3,
        portfolio_risk_amount="2500",
        symbol_risk_amount="500",
        last_trade_time_utc="2026-07-29T15:00:00Z",
        open_order_keys=[],
        kill_switch_active=False,
        source_sha256="a" * 64,
    )
    data.update(overrides)
    return RiskState(**data)


def request(**overrides):
    data = dict(
        request_id="risk-1",
        symbol="AAPL",
        action="BUY",
        quantity="100",
        entry_price="200",
        stop_price="190",
        take_profit_price="225",
        estimated_risk_amount="1000",
        position_sizing_sha256="b" * 64,
        requested_at_utc="2026-07-29T16:00:00Z",
        order_key="AAPL-BUY-100-200",
        metadata={},
    )
    data.update(overrides)
    return RiskRequest(**data)


def config(**overrides):
    data = dict(
        max_daily_loss_percent="0.03",
        max_consecutive_losses=3,
        max_open_positions=10,
        max_symbol_risk_percent="0.02",
        max_portfolio_risk_percent="0.06",
        minimum_risk_reward_ratio="2.0",
        session_start_hour_utc=13,
        session_end_hour_utc=21,
        cooldown_minutes=15,
        require_stop_loss=True,
        require_take_profit=True,
    )
    data.update(overrides)
    return RiskConfig(**data)


class RiskManagementV560Tests(unittest.TestCase):
    def engine(self):
        return RiskManagementEngine(mode="paper")

    def test_pass(self):
        r = self.engine().evaluate(state(), request(), config())
        self.assertEqual("PASS", r.status)

    def test_decision(self):
        r = self.engine().evaluate(state(), request(), config())
        self.assertEqual("risk_approved", r.decision)

    def test_symbol_uppercase(self):
        r = self.engine().evaluate(state(), request(symbol="aapl"), config())
        self.assertEqual("AAPL", r.symbol)

    def test_risk_amount(self):
        r = self.engine().evaluate(state(), request(), config())
        self.assertEqual("1000.00", r.risk_amount)

    def test_reward_amount(self):
        r = self.engine().evaluate(state(), request(), config())
        self.assertEqual("2500.00", r.reward_amount)

    def test_rr(self):
        r = self.engine().evaluate(state(), request(), config())
        self.assertEqual("2.500000", r.risk_reward_ratio)

    def test_daily_loss(self):
        r = self.engine().evaluate(state(), request(), config())
        self.assertEqual("750.00", r.daily_loss_amount)

    def test_kill_switch(self):
        r = self.engine().evaluate(state(kill_switch_active=True), request(), config())
        self.assertIn("kill_switch_active", r.rejection_reasons)

    def test_duplicate(self):
        r = self.engine().evaluate(
            state(open_order_keys=["AAPL-BUY-100-200"]),
            request(),
            config(),
        )
        self.assertIn("duplicate_order", r.rejection_reasons)

    def test_max_losses(self):
        r = self.engine().evaluate(state(consecutive_losses=3), request(), config())
        self.assertIn("max_consecutive_losses_reached", r.rejection_reasons)

    def test_max_positions(self):
        r = self.engine().evaluate(state(open_position_count=10), request(), config())
        self.assertIn("max_open_positions_reached", r.rejection_reasons)

    def test_session_block(self):
        r = self.engine().evaluate(state(), request(requested_at_utc="2026-07-29T22:00:00Z"), config())
        self.assertIn("outside_trading_session", r.rejection_reasons)

    def test_overnight_session(self):
        c = config(session_start_hour_utc=21, session_end_hour_utc=5)
        r = self.engine().evaluate(state(last_trade_time_utc=None), request(requested_at_utc="2026-07-29T23:00:00Z"), c)
        self.assertEqual("PASS", r.status)

    def test_full_day_session(self):
        c = config(session_start_hour_utc=0, session_end_hour_utc=0)
        r = self.engine().evaluate(state(last_trade_time_utc=None), request(requested_at_utc="2026-07-29T23:00:00Z"), c)
        self.assertEqual("PASS", r.status)

    def test_cooldown(self):
        r = self.engine().evaluate(
            state(last_trade_time_utc="2026-07-29T15:55:00Z"),
            request(),
            config(),
        )
        self.assertIn("cooldown_active", r.rejection_reasons)

    def test_requested_before_last_trade(self):
        r = self.engine().evaluate(
            state(last_trade_time_utc="2026-07-29T17:00:00Z"),
            request(),
            config(),
        )
        self.assertIn("requested_time_before_last_trade", r.rejection_reasons)

    def test_stop_required(self):
        r = self.engine().evaluate(state(), request(stop_price="0"), config())
        self.assertIn("stop_loss_required", r.rejection_reasons)

    def test_target_required(self):
        r = self.engine().evaluate(state(), request(take_profit_price="0"), config())
        self.assertIn("take_profit_required", r.rejection_reasons)

    def test_bad_buy_stop(self):
        r = self.engine().evaluate(state(), request(stop_price="205"), config())
        self.assertIn("invalid_stop_loss_geometry", r.rejection_reasons)

    def test_bad_buy_target(self):
        r = self.engine().evaluate(state(), request(take_profit_price="195"), config())
        self.assertIn("invalid_take_profit_geometry", r.rejection_reasons)

    def test_sell_pass(self):
        r = self.engine().evaluate(
            state(symbol_risk_amount="0"),
            request(action="SELL", entry_price="200", stop_price="210", take_profit_price="175"),
            config(),
        )
        self.assertEqual("PASS", r.status)

    def test_bad_sell_stop(self):
        r = self.engine().evaluate(
            state(),
            request(action="SELL", stop_price="190", take_profit_price="175"),
            config(),
        )
        self.assertIn("invalid_stop_loss_geometry", r.rejection_reasons)

    def test_bad_sell_target(self):
        r = self.engine().evaluate(
            state(),
            request(action="SELL", stop_price="210", take_profit_price="205"),
            config(),
        )
        self.assertIn("invalid_take_profit_geometry", r.rejection_reasons)

    def test_rr_minimum(self):
        r = self.engine().evaluate(
            state(),
            request(take_profit_price="215"),
            config(),
        )
        self.assertIn("risk_reward_ratio_below_minimum", r.rejection_reasons)

    def test_daily_limit(self):
        r = self.engine().evaluate(
            state(daily_realized_pnl="-2500", daily_unrealized_pnl="-500"),
            request(),
            config(),
        )
        self.assertIn("daily_loss_limit_reached", r.rejection_reasons)

    def test_symbol_limit(self):
        r = self.engine().evaluate(
            state(symbol_risk_amount="1500"),
            request(),
            config(),
        )
        self.assertIn("symbol_risk_limit_exceeded", r.rejection_reasons)

    def test_portfolio_limit(self):
        r = self.engine().evaluate(
            state(portfolio_risk_amount="5500"),
            request(),
            config(),
        )
        self.assertIn("portfolio_risk_limit_exceeded", r.rejection_reasons)

    def test_empty_request_id(self):
        r = self.engine().evaluate(state(), request(request_id=""), config())
        self.assertIn("request_id_required", r.rejection_reasons)

    def test_empty_symbol(self):
        r = self.engine().evaluate(state(), request(symbol=""), config())
        self.assertIn("symbol_required", r.rejection_reasons)

    def test_invalid_action(self):
        r = self.engine().evaluate(state(), request(action="HOLD"), config())
        self.assertIn("invalid_action", r.rejection_reasons)

    def test_bad_hash(self):
        r = self.engine().evaluate(state(), request(position_sizing_sha256="x"), config())
        self.assertIn("position_sizing_sha256_invalid", r.rejection_reasons)

    def test_empty_order_key(self):
        r = self.engine().evaluate(state(), request(order_key=""), config())
        self.assertIn("order_key_required", r.rejection_reasons)

    def test_bad_quantity(self):
        r = self.engine().evaluate(state(), request(quantity="0"), config())
        self.assertIn("quantity_must_be_positive", r.rejection_reasons)

    def test_bad_entry(self):
        r = self.engine().evaluate(state(), request(entry_price="0"), config())
        self.assertIn("entry_price_must_be_positive", r.rejection_reasons)

    def test_negative_estimated_risk(self):
        r = self.engine().evaluate(state(), request(estimated_risk_amount="-1"), config())
        self.assertIn("estimated_risk_amount_negative", r.rejection_reasons)

    def test_calculated_risk_wins(self):
        r = self.engine().evaluate(state(), request(estimated_risk_amount="100"), config())
        self.assertEqual("1000.00", r.risk_amount)

    def test_estimated_risk_wins(self):
        r = self.engine().evaluate(state(), request(estimated_risk_amount="1200"), config(max_symbol_risk_percent="0.03"))
        self.assertEqual("1200.00", r.risk_amount)

    def test_state_bad_equity(self):
        with self.assertRaises(ValueError):
            self.engine().evaluate(state(equity="0"), request(), config())

    def test_state_bad_risk(self):
        with self.assertRaises(ValueError):
            self.engine().evaluate(state(portfolio_risk_amount="-1"), request(), config())

    def test_state_bad_count(self):
        with self.assertRaises(ValueError):
            self.engine().evaluate(state(open_position_count=-1), request(), config())

    def test_state_bad_hash(self):
        with self.assertRaises(ValueError):
            self.engine().evaluate(state(source_sha256="x"), request(), config())

    def test_bad_daily_pct(self):
        with self.assertRaises(ValueError):
            self.engine().evaluate(state(), request(), config(max_daily_loss_percent="2"))

    def test_bad_symbol_pct(self):
        with self.assertRaises(ValueError):
            self.engine().evaluate(state(), request(), config(max_symbol_risk_percent="2"))

    def test_bad_portfolio_pct(self):
        with self.assertRaises(ValueError):
            self.engine().evaluate(state(), request(), config(max_portfolio_risk_percent="2"))

    def test_bad_rr(self):
        with self.assertRaises(ValueError):
            self.engine().evaluate(state(), request(), config(minimum_risk_reward_ratio="-1"))

    def test_bad_limit_count(self):
        with self.assertRaises(ValueError):
            self.engine().evaluate(state(), request(), config(max_open_positions=-1))

    def test_bad_session_hour(self):
        with self.assertRaises(ValueError):
            self.engine().evaluate(state(), request(), config(session_start_hour_utc=24))

    def test_bad_timestamp(self):
        with self.assertRaises(ValueError):
            self.engine().evaluate(state(), request(requested_at_utc="bad"), config())

    def test_naive_timestamp(self):
        with self.assertRaises(ValueError):
            self.engine().evaluate(state(), request(requested_at_utc="2026-07-29T16:00:00"), config())

    def test_request_hash(self):
        r = self.engine().evaluate(state(), request(), config())
        self.assertEqual(64, len(r.request_sha256))

    def test_risk_hash(self):
        r = self.engine().evaluate(state(), request(), config())
        self.assertEqual(64, len(r.risk_sha256))

    def test_network_false(self):
        r = self.engine().evaluate(state(), request(), config())
        self.assertFalse(r.network_used)

    def test_ledger_genesis(self):
        r = self.engine().evaluate(state(), request(), config())
        self.assertEqual("GENESIS", r.ledger[0]["previous_entry_sha256"])

    def test_ledger_chain(self):
        e = self.engine()
        e.evaluate(state(), request(request_id="1", order_key="1"), config())
        r = e.evaluate(state(), request(request_id="2", order_key="2"), config())
        self.assertEqual(r.ledger[0]["entry_sha256"], r.ledger[1]["previous_entry_sha256"])

    def test_deterministic_hash(self):
        a = self.engine().evaluate(state(), request(), config())
        b = self.engine().evaluate(state(), request(), config())
        self.assertEqual(a.risk_sha256, b.risk_sha256)

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            RiskManagementEngine(mode="bad")

    def test_live_blocked(self):
        with self.assertRaises(PermissionError):
            RiskManagementEngine(mode="live").evaluate(state(), request(), config())

    def test_live_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            RiskManagementEngine(mode="live", enable_live=True).evaluate(state(), request(), config())

    def test_export(self):
        e = self.engine()
        r = e.evaluate(state(), request(), config())
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "out.json"
            e.export(p, r)
            payload = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual("PASS", payload["result"]["status"])

    def test_load_payload(self):
        payload = {
            "state": asdict(state()),
            "request": asdict(request()),
            "config": asdict(config()),
        }
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "in.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            s, r, c = load_payload(p)
            self.assertEqual("100000", s.equity)
            self.assertEqual("risk-1", r.request_id)
            self.assertEqual(3, c.max_consecutive_losses)


if __name__ == "__main__":
    unittest.main()
