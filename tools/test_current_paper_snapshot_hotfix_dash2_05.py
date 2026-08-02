import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from autonomous_paper_runtime.current_paper_snapshot_collector import (
    LIVE_BASE_URL,
    CurrentPaperSnapshotCollector,
)
from dashboard.paper_trading_integration import (
    build_paper_trading_payload,
)


class Tests(unittest.TestCase):
    def root(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        return Path(td.name)

    def test_default_collector_does_not_use_network(self):
        root = self.root()
        result = CurrentPaperSnapshotCollector().run(
            output_path=root/"snapshot.json",
            result_path=root/"result.json",
        )
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertFalse(result["snapshot_written"])

    def test_live_endpoint_blocks(self):
        root = self.root()
        result = CurrentPaperSnapshotCollector().run(
            output_path=root/"snapshot.json",
            result_path=root/"result.json",
            base_url=LIVE_BASE_URL,
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_mock_actual_snapshot(self):
        root = self.root()

        def transport(**kwargs):
            url = kwargs["url"]
            if url.endswith("/v2/account"):
                return 200, {
                    "status": "ACTIVE",
                    "cash": "100000",
                    "buying_power": "200000",
                    "portfolio_value": "100000",
                    "equity": "100000",
                }
            if url.endswith("/v2/positions"):
                return 200, []
            if "/v2/orders?" in url:
                return 200, [{
                    "id": "order-1",
                    "symbol": "AAPL",
                    "qty": "1",
                    "filled_qty": "0",
                    "status": "accepted",
                }]
            return 200, {"is_open": False}

        with patch.dict(
            os.environ,
            {
                "APCA_API_KEY_ID": "paper-key",
                "APCA_API_SECRET_KEY": "paper-secret",
            },
            clear=False,
        ):
            result = CurrentPaperSnapshotCollector().run(
                output_path=root/"snapshot.json",
                result_path=root/"result.json",
                enable_network=True,
                transport=transport,
            )
        self.assertTrue(result["snapshot_written"])
        self.assertEqual(result["network_requests_executed"], 4)
        self.assertEqual(result["write_requests_executed"], 0)

    def test_dashboard_ignores_example_files(self):
        root = self.root()
        example = (
            root
            / "release/op3_09_to_op3_12/input/"
            "local_paper_positions_snapshot.json"
        )
        example.parent.mkdir(parents=True, exist_ok=True)
        example.write_text(
            json.dumps({
                "positions": [{"symbol": "FAKE", "qty": "99"}]
            }),
            encoding="utf-8",
        )
        payload = build_paper_trading_payload(root)
        self.assertEqual(payload["positions"], [])
        self.assertFalse(payload["snapshot"]["actual"])

    def test_dashboard_uses_fresh_actual_snapshot(self):
        root = self.root()
        path = (
            root
            / "release/dash2_05/actual/"
            "current_paper_snapshot.json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({
                "snapshot_type": "ACTUAL_ALPACA_PAPER_READ_ONLY",
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "paper_only": True,
                "read_only": True,
                "account": {
                    "status": "ACTIVE",
                    "cash": "100",
                    "buying_power": "200",
                },
                "positions": [],
                "open_orders": [],
                "clock": {"is_open": True},
            }),
            encoding="utf-8",
        )
        payload = build_paper_trading_payload(root)
        self.assertTrue(payload["snapshot"]["fresh"])
        self.assertEqual(payload["account"]["cash"], 100)
        self.assertEqual(payload["positions"], [])

    def test_dashboard_hides_stale_snapshot_values(self):
        root = self.root()
        path = (
            root
            / "release/dash2_05/actual/"
            "current_paper_snapshot.json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({
                "snapshot_type": "ACTUAL_ALPACA_PAPER_READ_ONLY",
                "observed_at": "2020-01-01T00:00:00+00:00",
                "paper_only": True,
                "read_only": True,
                "account": {
                    "status": "ACTIVE",
                    "cash": "999999",
                },
                "positions": [{"symbol": "FAKE", "qty": "99"}],
                "open_orders": [],
                "clock": {"is_open": True},
            }),
            encoding="utf-8",
        )
        payload = build_paper_trading_payload(root)
        self.assertFalse(payload["snapshot"]["fresh"])
        self.assertEqual(payload["account"]["status"], "NOT_AVAILABLE")
        self.assertEqual(payload["positions"], [])


if __name__ == "__main__":
    unittest.main()
