
import json
import tempfile
import unittest
from pathlib import Path

from paper_runtime.intraday_loop_v82_29_32 import run_intraday_loop


class Tests(unittest.TestCase):
    def write(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def run_case(
        self,
        *,
        session_ready=True,
        scheduler_ready=True,
        risk_clear=True,
        authorization_ready=True,
        execute=False,
        resume=False,
        active_lock=False,
        callbacks=None,
    ):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)

        self.write(root / "session.json", {
            "state": (
                "PAPER_SESSION_RUNNING"
                if session_ready else "PAPER_SESSION_READY_TO_START"
            ),
            "session_active": session_ready,
            "session_id": "session-test",
        })
        self.write(root / "scheduler.json", {
            "state": (
                "PAPER_SCHEDULER_TICK_AUTHORIZED"
                if scheduler_ready else "WAIT_PAPER_SESSION_RUNNING"
            ),
            "tick_authorized": scheduler_ready,
            "tick_id": "tick-test" if scheduler_ready else "",
        })
        self.write(root / "signal.json", {
            "shadow_action": "HOLD",
            "symbol": "",
            "quantity": 0,
        })
        self.write(root / "risk.json", {
            "state": (
                "SHADOW_RISK_CLEAR"
                if risk_clear else "SHADOW_RISK_KILL_SWITCH_ACTIVE"
            )
        })
        self.write(root / "authorization.json", {
            "state": (
                "SHADOW_TRADE_NO_ACTION"
                if authorization_ready else "SHADOW_AUTHORIZATION_SAFE_MODE"
            )
        })
        self.write(root / "execution.json", {
            "state": "WAIT_SHADOW_TRADING_FOUNDATION"
        })
        self.write(root / "portfolio.json", {
            "state": "WAIT_SHADOW_EXECUTION"
        })
        self.write(root / "analytics.json", {
            "state": "SHADOW_ANALYTICS_IN_PROGRESS"
        })
        self.write(root / "policy.json", {
            "paper_only": True,
            "read_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "continuous_loop_enabled": False,
        })

        if active_lock:
            self.write(root / "lock.json", {
                "active": True,
                "completed": False,
                "loop_id": "existing-loop",
                "session_id": "session-test",
                "tick_id": "tick-test",
                "last_completed_stage": "SIGNAL",
                "started_at": "2026-08-03T00:00:00+00:00",
            })

        result = run_intraday_loop(
            session_result_path=root / "session.json",
            scheduler_result_path=root / "scheduler.json",
            signal_path=root / "signal.json",
            risk_result_path=root / "risk.json",
            authorization_result_path=root / "authorization.json",
            execution_result_path=root / "execution.json",
            portfolio_result_path=root / "portfolio.json",
            analytics_result_path=root / "analytics.json",
            policy_path=root / "policy.json",
            loop_lock_path=root / "lock.json",
            loop_ledger_path=root / "ledger.jsonl",
            recovery_path=root / "recovery.json",
            dashboard_path=root / "dashboard.json",
            result_path=root / "result.json",
            execute_loop=execute,
            resume_loop=resume,
            stage_callbacks=callbacks,
        )
        return result, root

    def test_wait_session(self):
        result, _ = self.run_case(session_ready=False)
        self.assertEqual(result["state"], "INTRADAY_LOOP_WAIT_GATES")
        self.assertIn(
            "PAPER_SESSION_NOT_RUNNING",
            result["gate_reasons"],
        )

    def test_wait_tick(self):
        result, _ = self.run_case(scheduler_ready=False)
        self.assertIn(
            "SCHEDULER_TICK_NOT_AUTHORIZED",
            result["gate_reasons"],
        )

    def test_ready(self):
        result, _ = self.run_case()
        self.assertEqual(result["state"], "INTRADAY_LOOP_READY")

    def test_execute_complete(self):
        result, root = self.run_case(execute=True)
        self.assertTrue(result["loop_completed"])
        self.assertEqual(result["stage_count"], 9)
        self.assertTrue((root / "ledger.jsonl").exists())

    def test_duplicate_loop_blocked(self):
        result, _ = self.run_case(
            execute=True,
            active_lock=True,
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_stage_failure_recovery(self):
        callbacks = {
            "PORTFOLIO": lambda: {"status": "FAIL"}
        }
        result, root = self.run_case(
            execute=True,
            callbacks=callbacks,
        )
        self.assertEqual(
            result["state"],
            "INTRADAY_LOOP_RECOVERY_REQUIRED",
        )
        self.assertTrue((root / "recovery.json").exists())

    def test_resume_loop(self):
        result, _ = self.run_case(
            resume=True,
            active_lock=True,
        )
        self.assertTrue(result["loop_recovered"])
        self.assertTrue(result["loop_completed"])

    def test_dashboard_written(self):
        result, root = self.run_case()
        self.assertTrue(result["dashboard_state_written"])
        self.assertTrue((root / "dashboard.json").exists())

    def test_risk_gate(self):
        result, _ = self.run_case(risk_clear=False)
        self.assertIn("RISK_NOT_CLEAR", result["gate_reasons"])

    def test_read_only_contract(self):
        result, _ = self.run_case(execute=True)
        self.assertFalse(result["broker_write_enabled"])
        self.assertFalse(result["order_submission_enabled"])
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
