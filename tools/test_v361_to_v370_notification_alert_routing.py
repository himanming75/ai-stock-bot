from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from notification_alert_routing.service import (
    NotificationAlertRoutingService,
)


class Tests(unittest.TestCase):
    def setup_inputs(self, root: Path):
        risk = root / "risk.json"
        risk.write_text(
            json.dumps(
                {
                    "risk_level": "WARNING",
                    "portfolio_risk_score": "55",
                    "alerts": [
                        {
                            "code": "TEST_RISK",
                            "severity": "WARNING",
                            "actual": "30",
                            "limit": "25",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        health = root / "health.json"
        health.write_text(
            json.dumps(
                {
                    "status": "FAIL",
                    "health_score": 40,
                    "critical_issues": ["DUPLICATE_CONTROLLER_ROOTS"],
                    "warnings": ["DISK_USAGE_HIGH"],
                }
            ),
            encoding="utf-8",
        )
        performance = root / "performance.json"
        performance.write_text(
            json.dumps(
                {
                    "status": "PASS_WITH_WARNINGS",
                    "observation_count": 2,
                    "warnings": ["LIMITED_SAMPLE_SIZE"],
                }
            ),
            encoding="utf-8",
        )
        controller = root / "controller.json"
        controller.write_text(
            json.dumps({"status": "PASS"}),
            encoding="utf-8",
        )
        policy = root / "policy.json"
        policy.write_text(
            json.dumps(
                {
                    "deduplication_cooldown_seconds": 900,
                    "channel_enabled": {
                        "LOCAL_LOG": True,
                        "EMAIL": False,
                        "SLACK": False,
                        "DISCORD": False,
                        "WEBHOOK": False,
                    },
                    "severity_channels": {
                        "CRITICAL": ["LOCAL_LOG", "EMAIL"],
                        "WARNING": ["LOCAL_LOG"],
                        "INFO": ["LOCAL_LOG"],
                    },
                }
            ),
            encoding="utf-8",
        )
        return risk, health, performance, controller, policy

    def test_queue_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = self.setup_inputs(root)
            result = NotificationAlertRoutingService().evaluate(
                risk_path=inputs[0],
                health_path=inputs[1],
                performance_path=inputs[2],
                controller_path=inputs[3],
                policy_path=inputs[4],
                output_dir=root / "out",
                now=datetime(
                    2026, 1, 1, 12, 0, tzinfo=timezone.utc
                ),
            )
            self.assertEqual(result["queued_count"], 4)
            self.assertEqual(
                result["severity_counts"]["CRITICAL"], 1
            )

    def test_duplicate_suppression(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = self.setup_inputs(root)
            service = NotificationAlertRoutingService()
            out = root / "out"
            now = datetime(
                2026, 1, 1, 12, 0, tzinfo=timezone.utc
            )
            service.evaluate(
                risk_path=inputs[0],
                health_path=inputs[1],
                performance_path=inputs[2],
                controller_path=inputs[3],
                policy_path=inputs[4],
                output_dir=out,
                now=now,
            )
            second = service.evaluate(
                risk_path=inputs[0],
                health_path=inputs[1],
                performance_path=inputs[2],
                controller_path=inputs[3],
                policy_path=inputs[4],
                output_dir=out,
                now=now,
            )
            self.assertEqual(second["queued_count"], 0)
            self.assertEqual(second["suppressed_count"], 4)

    def test_prepare_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = self.setup_inputs(root)
            result = NotificationAlertRoutingService().evaluate(
                risk_path=inputs[0],
                health_path=inputs[1],
                performance_path=inputs[2],
                controller_path=inputs[3],
                policy_path=inputs[4],
                output_dir=root / "out",
            )
            self.assertFalse(
                result["actual_notification_send_performed"]
            )
            for item in result["queue"]:
                self.assertFalse(
                    item["actual_send_performed"]
                )

    def test_output_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = self.setup_inputs(root)
            out = root / "out"
            NotificationAlertRoutingService().evaluate(
                risk_path=inputs[0],
                health_path=inputs[1],
                performance_path=inputs[2],
                controller_path=inputs[3],
                policy_path=inputs[4],
                output_dir=out,
            )
            self.assertTrue(
                (out / "notification_queue.json").exists()
            )
            self.assertTrue(
                (out / "notification_ledger.jsonl").exists()
            )

    def test_no_orders_or_network(self):
        source = inspect.getsource(
            NotificationAlertRoutingService
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
