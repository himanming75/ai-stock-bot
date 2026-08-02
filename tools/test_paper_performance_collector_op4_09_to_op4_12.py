import json
import tempfile
import unittest
from pathlib import Path

from paper_pilot.performance_collector import (
    PaperPilotPerformanceCollector,
)


class Tests(unittest.TestCase):
    def write(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def append(self, path, payloads):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(json.dumps(item) + "\n" for item in payloads),
            encoding="utf-8",
        )

    def data(self):
        policy = {
            "paper_only": True,
            "read_only": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "minimum_samples_for_metrics": 2,
            "maximum_history_records": 100,
        }
        foundation = {
            "pilot_started": True,
            "pilot_id": "pilot-1",
            "session_id": "session-1",
        }
        monitor = {"health_status": "HEALTHY"}
        snapshot = {
            "snapshot_type": "ACTUAL_ALPACA_PAPER_READ_ONLY",
            "paper_only": True,
            "read_only": True,
            "account": {
                "equity": "100100",
                "portfolio_value": "100100",
                "cash": "90000",
                "buying_power": "200000",
            },
            "positions": [{"symbol": "AAPL", "qty": "1"}],
        }
        return policy, foundation, monitor, snapshot

    def run_case(
        self,
        values,
        *,
        collect=False,
        history=None,
        trades=None,
    ):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        names = ["policy", "foundation", "monitor", "snapshot"]
        paths = {name: root/f"{name}.json" for name in names}
        for name, value in zip(names, values):
            self.write(paths[name], value)
        if history:
            self.append(root/"history.jsonl", history)
        if trades:
            self.append(root/"trades.jsonl", trades)

        result = PaperPilotPerformanceCollector().run(
            policy_path=paths["policy"],
            foundation_result_path=paths["foundation"],
            session_monitor_result_path=paths["monitor"],
            current_snapshot_path=paths["snapshot"],
            trade_ledger_path=root/"trades.jsonl",
            equity_history_path=root/"history.jsonl",
            daily_report_path=root/"daily.json",
            performance_report_path=root/"performance.json",
            dashboard_state_path=root/"dashboard.json",
            result_path=root/"result.json",
            collect_snapshot=collect,
            observed_at="2026-08-02T08:00:00+00:00",
        )
        return result, root

    def test_wait_before_pilot_start(self):
        values = list(self.data())
        values[1] = {"pilot_started": False}
        result, _ = self.run_case(tuple(values))
        self.assertEqual(result["state"], "WAIT_PILOT_START")
        self.assertFalse(result["sample_written"])

    def test_collect_equity_sample(self):
        result, root = self.run_case(self.data(), collect=True)
        self.assertTrue(result["sample_written"])
        self.assertEqual(result["sample_count"], 1)
        self.assertTrue((root/"history.jsonl").exists())

    def test_return_and_drawdown(self):
        history = [
            {"equity": 100000, "observed_at": "a"},
            {"equity": 101000, "observed_at": "b"},
            {"equity": 99000, "observed_at": "c"},
        ]
        result, _ = self.run_case(
            self.data(), history=history
        )
        self.assertEqual(result["cumulative_pnl"], -1000)
        self.assertGreater(result["max_drawdown_pct"], 0)

    def test_win_loss_metrics(self):
        trades = [
            {"realized_pnl": 100},
            {"realized_pnl": -50},
            {"realized_pnl": 25},
        ]
        result, _ = self.run_case(
            self.data(), trades=trades
        )
        self.assertEqual(result["wins"], 2)
        self.assertEqual(result["losses"], 1)
        self.assertAlmostEqual(result["win_rate_pct"], 66.66666667)

    def test_invalid_snapshot_blocks(self):
        values = list(self.data())
        values[3] = {"snapshot_type": "EXAMPLE"}
        result, _ = self.run_case(tuple(values))
        self.assertEqual(result["status"], "BLOCKED")

    def test_read_only_contract(self):
        result, _ = self.run_case(self.data(), collect=True)
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
