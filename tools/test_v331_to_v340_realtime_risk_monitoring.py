from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from pathlib import Path

from realtime_risk_monitoring.service import (
    RealtimeRiskMonitoringService,
)


class Tests(unittest.TestCase):
    def create_inputs(self, root: Path, concentrated=False):
        weight = "40" if concentrated else "10"
        snapshot = {
            "generated_at": "2026-01-01T00:00:00+00:00",
            "status": "PASS",
            "market": {"is_open": True},
            "account": {
                "equity": "100000",
                "cash": "80000",
                "buying_power": "200000",
                "daily_return_percent": "-0.5",
            },
            "exposure": {
                "gross_exposure_percent": "20",
                "net_exposure_percent": "20",
            },
            "positions": [
                {
                    "symbol": "SPY",
                    "portfolio_weight_percent": weight,
                    "unrealized_pl_percent": "-1",
                }
            ],
        }
        snapshot_path = root / "portfolio.json"
        snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

        ledger_path = root / "metrics.jsonl"
        ledger_path.write_text(
            json.dumps({"equity": "102000"}) + "\n"
            + json.dumps({"equity": "101000"}) + "\n",
            encoding="utf-8",
        )

        policy = {
            "max_daily_loss_percent": "2",
            "max_drawdown_percent": "5",
            "max_single_position_percent": "25",
            "max_gross_exposure_percent": "100",
            "max_net_exposure_percent": "75",
            "min_cash_reserve_percent": "10",
            "max_buying_power_utilization_percent": "80",
            "warning_score": "50",
            "critical_score": "75",
        }
        policy_path = root / "policy.json"
        policy_path.write_text(json.dumps(policy), encoding="utf-8")
        return snapshot_path, ledger_path, policy_path

    def test_normal_risk(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot, ledger, policy = self.create_inputs(root)
            result = RealtimeRiskMonitoringService().evaluate(
                portfolio_snapshot_path=snapshot,
                portfolio_metrics_ledger_path=ledger,
                policy_path=policy,
                output_dir=root / "out",
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["critical_alert_count"], 0)
            self.assertEqual(result["metrics"]["peak_equity"], "102000")

    def test_concentration_alert(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot, ledger, policy = self.create_inputs(
                root, concentrated=True
            )
            result = RealtimeRiskMonitoringService().evaluate(
                portfolio_snapshot_path=snapshot,
                portfolio_metrics_ledger_path=ledger,
                policy_path=policy,
                output_dir=root / "out",
            )
            codes = {item["code"] for item in result["alerts"]}
            self.assertIn("SINGLE_POSITION_CONCENTRATION", codes)

    def test_drawdown_math(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot, ledger, policy = self.create_inputs(root)
            result = RealtimeRiskMonitoringService().evaluate(
                portfolio_snapshot_path=snapshot,
                portfolio_metrics_ledger_path=ledger,
                policy_path=policy,
                output_dir=root / "out",
            )
            self.assertEqual(
                result["metrics"]["drawdown_amount"], "2000"
            )

    def test_no_network_or_orders(self):
        source = inspect.getsource(RealtimeRiskMonitoringService)
        self.assertIn('"actual_external_network_used": False', source)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
        self.assertIn('"actual_live_orders_submitted": 0', source)

    def test_output_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot, ledger, policy = self.create_inputs(root)
            out = root / "out"
            RealtimeRiskMonitoringService().evaluate(
                portfolio_snapshot_path=snapshot,
                portfolio_metrics_ledger_path=ledger,
                policy_path=policy,
                output_dir=out,
            )
            self.assertTrue((out / "risk_dashboard.json").exists())
            self.assertTrue((out / "risk_monitor_ledger.jsonl").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
