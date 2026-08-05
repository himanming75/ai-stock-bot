from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path

from realtime_portfolio_monitoring.change_detector import (
    detect_position_changes,
)
from realtime_portfolio_monitoring.metrics import (
    build_position_metrics,
    build_realized_metrics,
)
from realtime_portfolio_monitoring.service import (
    RealtimePortfolioMonitoringService,
)


class FakeClient:
    def get_account(self):
        return {
            "status": "ACTIVE",
            "currency": "USD",
            "equity": "100000",
            "last_equity": "99500",
            "portfolio_value": "100000",
            "cash": "90000",
            "buying_power": "190000",
            "long_market_value": "10000",
            "short_market_value": "0",
        }

    def get_positions(self):
        return [
            {
                "symbol": "SPY",
                "qty": "10",
                "market_value": "6000",
                "cost_basis": "5900",
                "avg_entry_price": "590",
                "current_price": "600",
                "unrealized_pl": "100",
                "unrealized_plpc": "0.016949",
                "unrealized_intraday_pl": "40",
            }
        ]

    def get_orders(self, **kwargs):
        return [
            {
                "status": "filled",
                "side": "buy",
                "filled_qty": "10",
                "filled_avg_price": "590",
            }
        ]

    def get_clock(self):
        return {
            "is_open": True,
            "timestamp": "2026-01-01T12:00:00Z",
        }


class Tests(unittest.TestCase):
    def test_position_metrics(self):
        records, summary = build_position_metrics(
            FakeClient().get_positions(),
            equity=__import__(
                "decimal"
            ).Decimal("100000"),
        )
        self.assertEqual(
            records[0]["symbol"],
            "SPY",
        )
        self.assertEqual(
            summary["total_unrealized_pl"],
            "100",
        )
        self.assertEqual(
            summary["gross_exposure_percent"],
            "6.00",
        )

    def test_realized_activity_is_not_fake_pnl(self):
        result = build_realized_metrics(
            FakeClient().get_orders()
        )
        self.assertEqual(
            result["filled_buy_notional"],
            "5900",
        )
        self.assertIn(
            "not available",
            result["realized_pl_note"],
        )

    def test_position_change_detection(self):
        previous = {
            "positions": [
                {
                    "symbol": "SPY",
                    "qty": "5",
                }
            ]
        }
        current = [
            {
                "symbol": "SPY",
                "qty": "10",
            }
        ]
        changes = detect_position_changes(
            previous,
            current,
        )
        self.assertEqual(
            changes[0]["change_type"],
            "POSITION_INCREASED",
        )

    def test_collect_once_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                RealtimePortfolioMonitoringService(
                    FakeClient()
                ).collect_once(
                    output_dir=Path(directory),
                    cycle_number=1,
                )
            )
            self.assertEqual(
                result["status"],
                "PASS",
            )
            self.assertFalse(
                result[
                    "actual_broker_write_performed"
                ]
            )
            self.assertEqual(
                result[
                    "actual_paper_orders_submitted"
                ],
                0,
            )

    def test_zero_order_contract(self):
        source = inspect.getsource(
            RealtimePortfolioMonitoringService
        )
        self.assertIn(
            '"actual_paper_orders_submitted": 0',
            source,
        )
        self.assertIn(
            '"actual_live_orders_submitted": 0',
            source,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
