import tempfile
import unittest
from pathlib import Path

from continuous_service_runtime.state_machine import transition
from continuous_service_runtime.heartbeat import heartbeat
from continuous_service_runtime.scheduler import scheduler_tick
from continuous_service_runtime.recovery import build_recovery
from continuous_service_runtime.shutdown import graceful_shutdown
from continuous_service_runtime.runtime import run_runtime

class Tests(unittest.TestCase):
    def test_transition(self):
        value = transition("IDLE", "WAITING")
        self.assertTrue(value["allowed"])
        self.assertEqual(value["state"], "WAITING")

    def test_invalid_transition(self):
        value = transition("IDLE", "STOPPED")
        self.assertFalse(value["allowed"])

    def test_heartbeat(self):
        value = heartbeat(1, "WAITING")
        self.assertEqual(value["status"], "HEALTHY")
        self.assertEqual(value["actual_orders_submitted"], 0)

    def test_scheduler_wait(self):
        value = scheduler_tick({
            "state": "CONTINUOUS_AUTONOMOUS_ENGINE_WAITING_FOR_MANUAL_APPROVAL",
            "selected_session": {"session": {"session_id": "s1"}},
        })
        self.assertEqual(value["action"], "WAIT_FOR_MANUAL_APPROVAL")

    def test_scheduler_process(self):
        value = scheduler_tick({
            "state": "CONTINUOUS_AUTONOMOUS_ENGINE_READY",
            "selected_session": {"session": {"session_id": "s1"}},
        })
        self.assertEqual(value["action"], "PROCESS_SELECTED_SESSION")

    def test_recovery_clear(self):
        value = build_recovery("WAITING", [], {})
        self.assertFalse(value["recovery_required"])

    def test_shutdown(self):
        value = graceful_shutdown("TEST")
        self.assertEqual(value["state"], "STOPPED")
        self.assertTrue(value["checkpoint_saved"])

    def test_runtime_ticks(self):
        with tempfile.TemporaryDirectory() as temp:
            result = run_runtime(Path(temp), max_ticks=2)
            self.assertEqual(result["tick_count"], 2)
            self.assertEqual(result["heartbeat_count"], 2)

    def test_runtime_stops(self):
        with tempfile.TemporaryDirectory() as temp:
            result = run_runtime(Path(temp), max_ticks=1)
            self.assertTrue(result["runtime_stopped_cleanly"])
            self.assertFalse(result["background_service_running"])

    def test_orders_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(
                run_runtime(Path(temp), max_ticks=1)["actual_orders_submitted"],
                0,
            )

if __name__ == "__main__":
    unittest.main()
