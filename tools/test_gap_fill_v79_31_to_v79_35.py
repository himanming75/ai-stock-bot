from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from alpaca_market_data import (
    GapFillConfig,
    IngestionBar,
    build_gap_fill_certificate,
    execute_gap_fill_tasks,
    load_fixture_bars,
    load_gap_tasks,
    merge_gap_fill_rows,
    run_gap_fill,
    verify_gap_fill_manifest,
)


def bar(symbol: str, timestamp: str, price: float) -> IngestionBar:
    return IngestionBar(
        symbol=symbol,
        timeframe="1Min",
        timestamp=timestamp,
        open=price,
        high=price + 0.1,
        low=price - 0.1,
        close=price + 0.05,
        volume=100,
        trade_count=10,
        vwap=price + 0.02,
        source="ALPACA_FIXTURE",
    )


class Tests(unittest.TestCase):
    def setUp(self):
        self.config = GapFillConfig()
        self.tasks = [
            {
                "stage": "V79.28", "symbol": "AAPL", "timeframe": "1Min",
                "start": "2026-01-02T14:32:00Z", "end": "2026-01-02T14:32:00Z",
                "expected_bar_count": 1, "status": "PENDING",
            },
            {
                "stage": "V79.28", "symbol": "MSFT", "timeframe": "1Min",
                "start": "2026-01-02T14:32:00Z", "end": "2026-01-02T14:32:00Z",
                "expected_bar_count": 1, "status": "PENDING",
            },
        ]
        self.existing = [
            bar("AAPL", "2026-01-02T14:31:00Z", 100),
            bar("AAPL", "2026-01-02T14:33:00Z", 102),
            bar("MSFT", "2026-01-02T14:31:00Z", 200),
            bar("MSFT", "2026-01-02T14:33:00Z", 202),
            bar("SPY", "2026-01-02T14:31:00Z", 500),
        ]
        self.fixtures = [
            bar("AAPL", "2026-01-02T14:32:00Z", 101),
            bar("MSFT", "2026-01-02T14:32:00Z", 201),
        ]

    def test_v79_31_config_safety(self):
        self.config.validate()
        with self.assertRaises(ValueError):
            GapFillConfig(allow_network=True).validate()

    def test_v79_31_loads_pending_queue(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.json"
            path.write_text(json.dumps({
                "stage": "V79.28", "task_count": 2, "tasks": self.tasks
            }), encoding="utf-8")
            self.assertEqual(len(load_gap_tasks(path, self.config)), 2)

    def test_v79_31_rejects_completed_task(self):
        with TemporaryDirectory() as tmp:
            tasks = [dict(self.tasks[0], status="FILLED")]
            path = Path(tmp) / "queue.json"
            path.write_text(json.dumps({
                "stage": "V79.28", "task_count": 1, "tasks": tasks
            }), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_gap_tasks(path, self.config)

    def test_v79_32_executes_fixture_fill(self):
        rows, executions = execute_gap_fill_tasks(
            self.tasks, self.fixtures, self.config
        )
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(item.status == "FILLED" for item in executions))

    def test_v79_32_rejects_missing_fixture_bar(self):
        with self.assertRaises(ValueError):
            execute_gap_fill_tasks(self.tasks, self.fixtures[:1], self.config)

    def test_v79_32_fixture_loader_rejects_network_source(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.json"
            path.write_text(json.dumps({
                "source": "NETWORK", "rows": []
            }), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_fixture_bars(path)

    def test_v79_33_merges_new_gap_rows(self):
        merged, stats = merge_gap_fill_rows(self.existing, self.fixtures)
        self.assertEqual(len(merged), 7)
        self.assertEqual(stats["filled_new_row_count"], 2)

    def test_v79_33_reexecution_is_idempotent(self):
        once, _ = merge_gap_fill_rows(self.existing, self.fixtures)
        twice, stats = merge_gap_fill_rows(once, self.fixtures)
        self.assertEqual(once, twice)
        self.assertEqual(stats["duplicate_row_count"], 2)

    def test_v79_33_rejects_conflict(self):
        conflict = bar("AAPL", "2026-01-02T14:31:00Z", 999)
        with self.assertRaises(ValueError):
            merge_gap_fill_rows(self.existing, [conflict])

    def test_v79_34_writes_and_verifies_manifest(self):
        with TemporaryDirectory() as tmp:
            result = run_gap_fill(
                self.existing, self.tasks, self.fixtures,
                self.config, Path(tmp)
            )
            self.assertTrue(verify_gap_fill_manifest(Path(tmp), result["manifest"]))
            self.assertEqual(result["completion"]["remaining_gap_task_count"], 0)

    def test_v79_34_detects_tamper(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp)
            result = run_gap_fill(
                self.existing, self.tasks, self.fixtures,
                self.config, output
            )
            dataset = output / "alpaca_historical_bars.gap_filled.jsonl"
            dataset.write_text(dataset.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_gap_fill_manifest(output, result["manifest"])

    def test_v79_35_certificate(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            prior = root / "release/v79_30/output"
            prior.mkdir(parents=True)
            (prior / "historical_incremental_sync_certificate_v79_30.json").write_text(
                "{}\n", encoding="utf-8"
            )
            result = run_gap_fill(
                self.existing, self.tasks, self.fixtures,
                self.config, root / "release/v79_35/output/gap_fill"
            )
            cert = build_gap_fill_certificate(
                root, root / "release/v79_35/output", self.config, result
            )
            self.assertEqual(cert["status"], "PASS")
            self.assertEqual(cert["actual_orders_submitted"], 0)

    def test_no_order_submission_or_credentials(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "alpaca_market_data/gap_fill_v79_31_35.py"
        ).read_text(encoding="utf-8").lower()
        self.assertNotIn("submit_order(", source)
        self.assertNotIn("tradingclient(", source)
        self.assertNotIn("api_secret", source)


if __name__ == "__main__":
    unittest.main()
