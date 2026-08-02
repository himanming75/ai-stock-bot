from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path

from autonomous_paper_runtime.autonomous_runtime_supervisor import AutonomousRuntimeSupervisor


class Tests(unittest.TestCase):
    def run_supervisor(self, root: Path):
        return AutonomousRuntimeSupervisor().run(
            repository_root=root,
            runtime_token_path=root / "release/v140_01/actual/token.json",
            supervisor_state_path=root / "release/v140_01/actual/state.json",
            lock_path=root / "release/v140_01/actual/lock.json",
            result_path=root / "release/v140_01/actual/result.json",
        )

    def write(self, root, rel, payload):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_empty_pipeline_waits(self):
        with tempfile.TemporaryDirectory() as t:
            result = self.run_supervisor(Path(t))
            self.assertEqual(result["state"], "RUNTIME_WAITING")
            self.assertEqual(result["selected_stage"], "V139.02")

    def test_selects_earliest_waiting_stage(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.write(root, "release/v139_02/actual/terminal_commit_handoff_result.json", {
                "status": "PASS", "state": "WAIT_TERMINAL_COMMIT", "safe_mode_engaged": False
            })
            self.write(root, "release/v139_03/actual/next_cycle_unlock_result.json", {
                "status": "PASS", "state": "WAIT_HANDOFF", "safe_mode_engaged": False
            })
            result = self.run_supervisor(root)
            self.assertEqual(result["selected_stage"], "V139.02")
            self.assertEqual(result["selected_state"], "WAIT_TERMINAL_COMMIT")

    def test_safe_mode_propagates(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.write(root, "release/v139_06/actual/next_order_eligibility_result.json", {
                "status": "BLOCKED", "state": "ELIGIBILITY_SAFE_MODE", "safe_mode_engaged": True
            })
            result = self.run_supervisor(root)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["selected_stage"], "V139.06")

    def test_bootstrap_creates_runtime_token(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.write(root, "release/v139_11_to_v139_15/actual/ultra_fast_cycle_finalization_result.json", {
                "status": "PASS",
                "state": "NEXT_CYCLE_BOOTSTRAP_READY",
                "bootstrap_id": "bootstrap-001",
                "next_cycle_bootstrap_ready": True,
                "safe_mode_engaged": False,
            })
            self.write(root, "release/v139_11_to_v139_15/actual/next_cycle_bootstrap_token.json", {
                "bootstrap_id": "bootstrap-001",
                "next_cycle_bootstrap_ready": True,
            })
            result = self.run_supervisor(root)
            self.assertEqual(result["state"], "AUTONOMOUS_RUNTIME_READY")
            self.assertTrue(result["runtime_token_written"])
            self.assertEqual(result["next_phase"], "V140_02_MARKET_SESSION_CONTROLLER")

    def test_duplicate_runtime_is_idempotent(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.write(root, "release/v139_11_to_v139_15/actual/ultra_fast_cycle_finalization_result.json", {
                "status": "PASS",
                "state": "NEXT_CYCLE_BOOTSTRAP_READY",
                "bootstrap_id": "bootstrap-001",
                "next_cycle_bootstrap_ready": True,
                "safe_mode_engaged": False,
            })
            self.write(root, "release/v139_11_to_v139_15/actual/next_cycle_bootstrap_token.json", {
                "bootstrap_id": "bootstrap-001",
            })
            first = self.run_supervisor(root)
            second = self.run_supervisor(root)
            self.assertTrue(first["runtime_token_written"])
            self.assertTrue(second["duplicate_runtime"])
            self.assertTrue(second["runtime_ready"])

    def test_active_lock_blocks(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.write(root, "release/v140_01/actual/lock.json", {
                "released": False,
            })
            result = self.run_supervisor(root)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertTrue(result["safe_mode_engaged"])


if __name__ == "__main__":
    unittest.main()
