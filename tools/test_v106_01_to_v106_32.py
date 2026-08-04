import json
import tempfile
import unittest
from pathlib import Path

from daily_paper_runner.session import select_session
from daily_paper_runner.preflight import evaluate_preflight
from daily_paper_runner.approval import build_paper_approval
from daily_paper_runner.plan import build_daily_plan
from daily_paper_runner.dedup import detect_duplicate
from daily_paper_runner.engine import evaluate

class Tests(unittest.TestCase):
    def test_select_requested_session(self):
        value = select_session({
            "queue": {"sessions": [{
                "session_id": "s1",
                "session_date": "2026-08-10",
                "state": "QUEUED",
            }]}
        }, "2026-08-10")
        self.assertTrue(value["session_available"])

    def test_missing_requested_session(self):
        value = select_session({"queue": {"sessions": []}}, "2026-08-10")
        self.assertFalse(value["session_available"])

    def test_preflight(self):
        value = evaluate_preflight(
            {
                "state": "PRODUCTION_READINESS_FINAL_RELEASE_COMPLETE",
                "paper_trading_ready": True,
                "live_trading_ready": False,
            },
            {"state": "MULTI_DAY_SCHEDULER_READY"},
            {"state": "CONTINUOUS_SERVICE_RUNTIME_READY"},
            {
                "session_available": True,
                "session": {
                    "paper_only": True,
                    "actual_orders_submitted": 0,
                },
            },
            {
                "paper_auto_approval_enabled": True,
                "live_auto_approval_enabled": False,
            },
        )
        self.assertTrue(value["passed"])

    def test_paper_approval(self):
        value = build_paper_approval(
            {"passed": True},
            {"paper_auto_approval_enabled": True},
        )
        self.assertTrue(value["paper_simulation_authorized"])
        self.assertFalse(value["live_execution_authorized"])

    def test_plan(self):
        value = build_daily_plan(
            {"session_id": "s1", "session_date": "2026-08-10"},
            {"autonomous_decision": {"decision": "ACT"}},
            {
                "allocation": {
                    "allocations": [{
                        "strategy_id": "MOMENTUM_5",
                        "target_weight_pct": 40.0,
                    }]
                }
            },
            {"paper_simulation_authorized": True},
        )
        self.assertEqual(value["plan_count"], 1)

    def test_duplicate(self):
        value = detect_duplicate(
            "key",
            [{
                "run_key": "key",
                "run_id": "r1",
                "state": "DAILY_PAPER_TRADING_RUN_COMPLETED",
            }],
        )
        self.assertTrue(value["duplicate"])

    def test_missing_sources_block(self):
        with tempfile.TemporaryDirectory() as temp:
            result = evaluate(Path(temp), "2026-08-10")
            self.assertEqual(
                result["state"],
                "DAILY_PAPER_TRADING_SOURCE_REQUIRED",
            )

    def test_orders_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(
                evaluate(Path(temp), "2026-08-10")[
                    "actual_orders_submitted"
                ],
                0,
            )

    def test_live_disabled(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertFalse(
                evaluate(Path(temp), "2026-08-10")[
                    "live_execution_authorized"
                ]
            )

if __name__ == "__main__":
    unittest.main()
