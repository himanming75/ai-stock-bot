import json
import tempfile
import unittest
from pathlib import Path

from shadow_runtime.autonomous_cycle_v82_01_04 import run_autonomous_shadow_cycle

class Tests(unittest.TestCase):
    def write(self, p, d):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d), encoding="utf-8")

    def case(self, *, ready=True, execute=False, active=False, callbacks=None):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        r = Path(td.name)
        self.write(r/"policy.json", {
            "shadow_only": True,
            "single_cycle_only": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "network_enabled": False,
        })
        self.write(r/"foundation.json", {"state": "SHADOW_TRADING_READY" if ready else "WAIT_PAPER_TRADING_COMPLETION"})
        self.write(r/"execution.json", {"state": "SHADOW_EXECUTION_NO_ACTION"})
        self.write(r/"portfolio.json", {"state": "SHADOW_PORTFOLIO_NO_CHANGE"})
        if active:
            self.write(r/"lock.json", {"active": True, "cycle_id": "existing"})
        out = run_autonomous_shadow_cycle(
            policy_path=r/"policy.json",
            foundation_result_path=r/"foundation.json",
            execution_result_path=r/"execution.json",
            portfolio_result_path=r/"portfolio.json",
            cycle_lock_path=r/"lock.json",
            cycle_ledger_path=r/"ledger.jsonl",
            dashboard_path=r/"dashboard.json",
            recovery_path=r/"recovery.json",
            result_path=r/"result.json",
            execute_cycle=execute,
            stage_callbacks=callbacks,
        )
        return out, r

    def test_ready_plan(self):
        out, _ = self.case()
        self.assertEqual(out["state"], "AUTONOMOUS_SHADOW_CYCLE_READY")

    def test_wait_foundation(self):
        out, _ = self.case(ready=False, execute=True)
        self.assertEqual(out["state"], "WAIT_SHADOW_FOUNDATION")

    def test_cycle_complete(self):
        out, r = self.case(execute=True)
        self.assertEqual(out["state"], "AUTONOMOUS_SHADOW_CYCLE_COMPLETE")
        self.assertTrue((r/"ledger.jsonl").exists())

    def test_duplicate_cycle_blocked(self):
        out, _ = self.case(execute=True, active=True)
        self.assertEqual(out["status"], "BLOCKED")

    def test_recovery_required(self):
        callbacks = {"RISK": lambda: {"status": "FAIL"}}
        out, _ = self.case(execute=True, callbacks=callbacks)
        self.assertTrue(out["recovery_ready"])

    def test_dashboard_written(self):
        out, r = self.case()
        self.assertTrue(out["dashboard_state_written"])
        self.assertTrue((r/"dashboard.json").exists())

    def test_single_cycle_only(self):
        out, _ = self.case()
        self.assertTrue(out["single_cycle_only"])
        self.assertFalse(out["continuous_loop_enabled"])

    def test_read_only_contract(self):
        out, _ = self.case(execute=True)
        self.assertFalse(out["broker_write_enabled"])
        self.assertFalse(out["order_submission_enabled"])
        self.assertEqual(out["network_requests_executed"], 0)
        self.assertEqual(out["write_requests_executed"], 0)
        self.assertEqual(out["actual_paper_orders_submitted"], 0)

if __name__ == "__main__":
    unittest.main()
