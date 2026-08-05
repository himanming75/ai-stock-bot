from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from pathlib import Path

from strategy_framework.io import write_json
from strategy_framework.service import StrategyFrameworkService


class Tests(unittest.TestCase):
    def inputs(self, root: Path):
        config = root / "config.json"
        write_json(
            config,
            {
                "strategies": [
                    {
                        "name": "momentum",
                        "enabled": True,
                        "weight": "1",
                        "config": {"lookback": 5},
                    },
                    {
                        "name": "trend",
                        "enabled": True,
                        "weight": "1",
                        "config": {
                            "fast_window": 3,
                            "slow_window": 7,
                        },
                    },
                ],
                "voting": {
                    "minimum_combined_score": "1"
                },
            },
        )
        fixture = root / "fixture.json"
        bars = []
        for index in range(10):
            price = 100 + index
            bars.append(
                {
                    "open": str(price - 0.2),
                    "high": str(price + 0.5),
                    "low": str(price - 0.5),
                    "close": str(price),
                }
            )
        write_json(
            fixture,
            {"symbols": {"SPY": {"bars": bars}}},
        )
        return config, fixture

    def test_generates_buy_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, fixture = self.inputs(root)
            result = StrategyFrameworkService().evaluate(
                strategy_config_path=config,
                market_fixture_path=fixture,
                output_dir=root / "out",
            )
            self.assertEqual(
                result["symbol_decisions"][0]["signal"],
                "BUY",
            )

    def test_no_order_ticket(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, fixture = self.inputs(root)
            result = StrategyFrameworkService().evaluate(
                strategy_config_path=config,
                market_fixture_path=fixture,
                output_dir=root / "out",
            )
            self.assertFalse(
                result["actual_order_ticket_created"]
            )

    def test_insufficient_data_is_honest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, _ = self.inputs(root)
            fixture = root / "short.json"
            write_json(
                fixture,
                {
                    "symbols": {
                        "SPY": {
                            "bars": [
                                {
                                    "open": "100",
                                    "high": "101",
                                    "low": "99",
                                    "close": "100",
                                }
                            ]
                        }
                    }
                },
            )
            result = StrategyFrameworkService().evaluate(
                strategy_config_path=config,
                market_fixture_path=fixture,
                output_dir=root / "out",
            )
            self.assertEqual(
                result["symbol_decisions"][0]["status"],
                "INSUFFICIENT_DATA",
            )

    def test_output_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, fixture = self.inputs(root)
            out = root / "out"
            StrategyFrameworkService().evaluate(
                strategy_config_path=config,
                market_fixture_path=fixture,
                output_dir=out,
            )
            self.assertTrue(
                (out / "strategy_dashboard.json").exists()
            )
            self.assertTrue(
                (out / "strategy_signal_ledger.jsonl").exists()
            )

    def test_no_network_or_orders(self):
        source = inspect.getsource(
            StrategyFrameworkService
        )
        self.assertIn(
            '"actual_external_network_used": False',
            source,
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
