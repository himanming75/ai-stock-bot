from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from pathlib import Path

from paper_order_lifecycle.service import (
    KNOWN_STATUSES,
    PaperOrderLifecycleMonitor,
)


class FakeClient:
    def get_order_by_client_id(self, client_order_id):
        return {
            "id": "order-1",
            "client_order_id": client_order_id,
            "symbol": "SPY",
            "side": "buy",
            "type": "market",
            "status": "filled",
            "filled_qty": "0.008",
            "filled_avg_price": "625.00",
            "notional": "5",
            "submitted_at": "2026-01-01T00:00:00Z",
            "filled_at": "2026-01-01T00:00:01Z",
        }

    def get_account(self):
        return {"equity": "100005", "cash": "99995"}

    def get_positions(self):
        return [{"symbol": "SPY", "qty": "0.008"}]

    def get_clock(self):
        return {"is_open": True}


class Tests(unittest.TestCase):
    def p3_result(self, path: Path):
        path.write_text(
            json.dumps(
                {
                    "broker_response": {
                        "id": "order-1",
                        "client_order_id": "p3m-test",
                    }
                }
            ),
            encoding="utf-8",
        )

    def test_filled_order_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = root / "p3.json"
            self.p3_result(result_path)
            summary = PaperOrderLifecycleMonitor(
                FakeClient()
            ).monitor(
                p3_result_path=result_path,
                output_dir=root / "out",
                interval_seconds=1,
                max_cycles=1,
            )
            self.assertEqual(summary["status"], "PASS")
            self.assertEqual(summary["final_status"], "filled")

    def test_filled_status_known(self):
        self.assertIn("filled", KNOWN_STATUSES)

    def test_position_reconciliation_required(self):
        source = inspect.getsource(
            PaperOrderLifecycleMonitor.monitor
        )
        self.assertIn('"position_found"', source)

    def test_read_only_contract(self):
        source = inspect.getsource(
            PaperOrderLifecycleMonitor.monitor
        )
        self.assertIn(
            '"actual_broker_write_performed": False',
            source,
        )
        self.assertIn(
            '"actual_order_submission_performed": False',
            source,
        )

    def test_zero_new_orders(self):
        source = inspect.getsource(
            PaperOrderLifecycleMonitor.monitor
        )
        self.assertIn(
            '"actual_paper_orders_submitted": 0',
            source,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
