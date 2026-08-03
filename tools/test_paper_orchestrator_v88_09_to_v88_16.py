from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from paper_orchestrator.engine import build_run_id, run_orchestrator
from paper_orchestrator.lock import RunLock
from paper_orchestrator.state import STEP_ORDER, new_state


class PaperOrchestratorTests(unittest.TestCase):
    def test_indicator_layout_is_supported(self):
        from paper_orchestrator.steps import INDICATOR_ENGINE_LAYOUT
        self.assertIn(
            INDICATOR_ENGINE_LAYOUT,
            {"indicator_engine", "indicator_engine_v2"},
        )

    def test_run_id_stable(self):
        value = build_run_id("2026-08-03T20:00:00+00:00")
        self.assertEqual(
            value,
            "paper-cycle-20260803T200000_0000",
        )

    def test_new_state_is_safe(self):
        state = new_state("x", "2026-08-03T20:00:00+00:00")
        self.assertTrue(state["paper_only"])
        self.assertFalse(state["broker_write_enabled"])

    def test_lock_prevents_duplicate(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "lock.json"
            first = RunLock(path, "one")
            first.acquire()
            try:
                second = RunLock(path, "two")
                with self.assertRaises(RuntimeError):
                    second.acquire()
            finally:
                first.release()

    def test_step_order_count(self):
        self.assertEqual(len(STEP_ORDER), 7)

    def test_full_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fake = {
                name: (lambda _: {"state": "READY"})
                for name in STEP_ORDER
            }
            with patch("paper_orchestrator.engine.STEP_FUNCTIONS", fake):
                result = run_orchestrator(
                    root,
                    observed_at_override="2026-08-03T20:00:00+00:00",
                )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["completed_step_count"], 7)

    def test_safe_mode_after_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fake = {
                name: (lambda _: {"state": "READY"})
                for name in STEP_ORDER
            }
            with patch("paper_orchestrator.engine.STEP_FUNCTIONS", fake):
                result = run_orchestrator(
                    root,
                    observed_at_override="2026-08-03T20:01:00+00:00",
                    fail_after_step="STRATEGY_ENGINE",
                )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(result["safe_mode"])

    def test_resume_skips_completed(self):
        calls = []

        def make_step(name):
            def execute(_):
                calls.append(name)
                return {"state": "READY"}
            return execute

        fake = {name: make_step(name) for name in STEP_ORDER}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch("paper_orchestrator.engine.STEP_FUNCTIONS", fake):
                first = run_orchestrator(
                    root,
                    observed_at_override="2026-08-03T20:02:00+00:00",
                    fail_after_step="STRATEGY_ENGINE",
                )
                second = run_orchestrator(
                    root,
                    observed_at_override="2026-08-03T20:02:00+00:00",
                )
        self.assertEqual(first["status"], "BLOCKED")
        self.assertEqual(second["status"], "PASS")
        self.assertEqual(calls.count("INDICATOR_ENGINE"), 1)
        self.assertEqual(calls.count("STRATEGY_ENGINE"), 1)

    def test_result_disables_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fake = {
                name: (lambda _: {"state": "READY"})
                for name in STEP_ORDER
            }
            with patch("paper_orchestrator.engine.STEP_FUNCTIONS", fake):
                result = run_orchestrator(
                    root,
                    observed_at_override="2026-08-03T20:03:00+00:00",
                )
        self.assertFalse(result["order_submission_enabled"])
        self.assertFalse(result["live_trading_enabled"])


if __name__ == "__main__":
    unittest.main()
