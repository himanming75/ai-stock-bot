from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from phase1_premarket_completion.backup import (
    build_backup_plan,
    execute_backup,
)
from phase1_premarket_completion.command_queue import (
    enqueue_plan,
    execute_queue,
)
from phase1_premarket_completion.config_pipeline import (
    activate_candidate,
)
from phase1_premarket_completion.health import (
    calculate_health,
)
from phase1_premarket_completion.notifications import (
    send_notification,
)
from phase1_premarket_completion.runtime_loader import (
    apply_runtime_plan,
)
from phase1_premarket_completion.service import (
    Phase1PremarketCompletionService,
)


class Tests(unittest.TestCase):
    def test_certification(self):
        with tempfile.TemporaryDirectory() as d:
            result = (
                Phase1PremarketCompletionService()
                .evaluate(output_dir=Path(d))
            )
            self.assertEqual(
                result["status"],
                "PASS",
            )
            self.assertTrue(
                result[
                    "bilingual_report_ready"
                ]
            )

    def test_all_execution_paths_blocked(self):
        for function in (
            activate_candidate,
            apply_runtime_plan,
            execute_queue,
            execute_backup,
            send_notification,
        ):
            with self.assertRaises(
                PermissionError
            ):
                function()

    def test_health_score(self):
        result = calculate_health(
            cpu_percent=20,
            memory_growth_mb=10,
            polling_delay_seconds=30,
            broker_latency_ms=200,
            error_count=0,
            stale_source_count=0,
        )
        self.assertEqual(
            result["status"],
            "READY",
        )
        self.assertGreaterEqual(
            result["score"],
            85,
        )

    def test_command_plan_not_executed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = enqueue_plan(
                action="PAUSE",
                reason="test",
                requested_by="TEST",
                latest_path=root / "latest.json",
                queue_path=root / "queue.jsonl",
            )
            self.assertEqual(
                result["execution_status"],
                "NOT_EXECUTED",
            )
            self.assertFalse(
                result[
                    "process_stop_enabled"
                ]
            )

    def test_backup_dry_run(self):
        with tempfile.TemporaryDirectory() as d:
            result = build_backup_plan(
                action="SNAPSHOT",
                source_paths=["release/test"],
                destination="release/backup",
                output_path=(
                    Path(d) / "backup.json"
                ),
            )
            self.assertEqual(
                result["mode"],
                "DRY_RUN_ONLY",
            )
            self.assertFalse(
                result[
                    "filesystem_write_enabled"
                ]
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as d:
            result = (
                Phase1PremarketCompletionService()
                .evaluate(output_dir=Path(d))
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
            self.assertEqual(
                result[
                    "actual_live_orders_submitted"
                ],
                0,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
