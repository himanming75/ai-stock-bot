from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from pathlib import Path

from performance_analytics.service import (
    PerformanceAnalyticsService,
)


class Tests(unittest.TestCase):
    def inputs(self, root: Path):
        metrics = root / "metrics.jsonl"
        rows = [
            {
                "generated_at": "2026-01-02T15:00:00+00:00",
                "equity": "100000",
                "daily_pl": "0",
                "daily_return_percent": "0",
            },
            {
                "generated_at": "2026-01-02T15:01:00+00:00",
                "equity": "101000",
                "daily_pl": "1000",
                "daily_return_percent": "1",
            },
            {
                "generated_at": "2026-01-02T15:02:00+00:00",
                "equity": "100500",
                "daily_pl": "500",
                "daily_return_percent": "0.5",
            },
        ]
        metrics.write_text(
            "\n".join(json.dumps(row) for row in rows) + "\n",
            encoding="utf-8",
        )

        portfolio = root / "portfolio.json"
        portfolio.write_text(
            json.dumps(
                {
                    "generated_at": "2026-01-02T15:02:00+00:00",
                    "status": "PASS",
                }
            ),
            encoding="utf-8",
        )

        risk = root / "risk.json"
        risk.write_text(
            json.dumps(
                {
                    "generated_at": "2026-01-02T15:02:01+00:00",
                    "risk_level": "NORMAL",
                    "portfolio_risk_score": "5",
                    "alert_count": 0,
                }
            ),
            encoding="utf-8",
        )
        return metrics, portfolio, risk

    def test_total_return(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metrics, portfolio, risk = self.inputs(root)
            result = PerformanceAnalyticsService().evaluate(
                portfolio_metrics_ledger_path=metrics,
                portfolio_snapshot_path=portfolio,
                risk_snapshot_path=risk,
                output_dir=root / "out",
            )
            self.assertEqual(
                result["summary"]["total_return_percent"],
                "0.500",
            )

    def test_maximum_drawdown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metrics, portfolio, risk = self.inputs(root)
            result = PerformanceAnalyticsService().evaluate(
                portfolio_metrics_ledger_path=metrics,
                portfolio_snapshot_path=portfolio,
                risk_snapshot_path=risk,
                output_dir=root / "out",
            )
            self.assertGreater(
                float(result["summary"][
                    "maximum_drawdown_percent"
                ]),
                0,
            )

    def test_trade_metrics_are_not_fabricated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metrics, portfolio, risk = self.inputs(root)
            result = PerformanceAnalyticsService().evaluate(
                portfolio_metrics_ledger_path=metrics,
                portfolio_snapshot_path=portfolio,
                risk_snapshot_path=risk,
                output_dir=root / "out",
            )
            self.assertIsNone(
                result["trade_statistics"]["win_rate"]
            )
            self.assertEqual(
                result["trade_statistics"]["status"],
                "INSUFFICIENT_REALIZED_TRADE_DATA",
            )

    def test_output_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metrics, portfolio, risk = self.inputs(root)
            out = root / "out"
            PerformanceAnalyticsService().evaluate(
                portfolio_metrics_ledger_path=metrics,
                portfolio_snapshot_path=portfolio,
                risk_snapshot_path=risk,
                output_dir=out,
            )
            self.assertTrue(
                (out / "performance_dashboard.json").exists()
            )
            self.assertTrue(
                (out / "equity_curve.json").exists()
            )

    def test_no_network_or_orders(self):
        source = inspect.getsource(
            PerformanceAnalyticsService
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
