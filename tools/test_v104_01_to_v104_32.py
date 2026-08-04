import tempfile,unittest
from pathlib import Path

from continuous_autonomous_engine.session import select_next_session
from continuous_autonomous_engine.gates import evaluate_iteration_gates
from continuous_autonomous_engine.phase_executor import execute_phase
from continuous_autonomous_engine.recovery import build_recovery
from continuous_autonomous_engine.state import resolve_state
from continuous_autonomous_engine.engine import evaluate

class Tests(unittest.TestCase):
    def test_select_session(self):
        value=select_next_session({
            "queue":{"sessions":[
                {"session_id":"b","session_date":"2026-08-04","state":"QUEUED"},
                {"session_id":"a","session_date":"2026-08-03","state":"QUEUED"},
            ]}
        })
        self.assertEqual(value["session"]["session_id"],"a")

    def test_no_session(self):
        value=select_next_session({
            "queue":{"sessions":[{"state":"COMPLETE"}]}
        })
        self.assertFalse(value["session_available"])

    def test_gates(self):
        sources={
            "decision":{
                "manual_approval_required":True,
                "approval_gate":{"approval_granted":False},
                "execution_authorized":False,
            },
            "risk":{"pre_execution_gate":{"passed":True}},
            "adaptive_rebalance":{"optimization_gate":{"passed":True}},
        }
        selected={
            "session_available":True,
            "session":{
                "actual_orders_submitted":0,
                "paper_only":True,
            },
        }
        self.assertTrue(
            evaluate_iteration_gates(
                sources,selected,{"maximum_iterations_per_run":1}
            )["passed"]
        )

    def test_phase(self):
        phase={
            "phase_number":1,
            "phase_id":"LOAD_SCHEDULER_STATE",
            "state":"PENDING",
            "attempt_count":0,
            "error":None,
        }
        self.assertEqual(
            execute_phase(phase,{"sources_valid":True})["state"],
            "COMPLETED",
        )

    def test_recovery(self):
        value=build_recovery(
            {"failed":["scheduler_ready"]},
            ["LOAD_SCHEDULER_STATE"],
            {"maximum_recovery_attempts":3},
        )
        self.assertTrue(value["recovery_required"])

    def test_waiting_state(self):
        value=resolve_state(
            {"passed":True},
            {"session_available":True},
            {"passed":True},
            [],
            "AUTONOMOUS_CYCLE_WAITING_FOR_MANUAL_APPROVAL",
        )
        self.assertEqual(
            value["state"],
            "CONTINUOUS_AUTONOMOUS_ENGINE_WAITING_FOR_MANUAL_APPROVAL",
        )

    def test_idle_state(self):
        value=resolve_state(
            {"passed":True},
            {"session_available":False},
            {"passed":True},
            [],
            "AUTONOMOUS_CYCLE_HOLD",
        )
        self.assertEqual(
            value["state"],
            "CONTINUOUS_AUTONOMOUS_ENGINE_IDLE",
        )

    def test_missing_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            result=evaluate(Path(temp))
            self.assertEqual(
                result["state"],
                "CONTINUOUS_AUTONOMOUS_ENGINE_SOURCE_REQUIRED",
            )

    def test_orders_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(evaluate(Path(temp))["actual_orders_submitted"],0)

    def test_service_not_started(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertFalse(
                evaluate(Path(temp))["continuous_service_started"]
            )

if __name__=="__main__":
    unittest.main()
