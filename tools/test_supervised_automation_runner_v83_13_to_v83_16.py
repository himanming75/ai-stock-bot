
import json, tempfile, unittest
from pathlib import Path
from paper_runtime.supervised_automation_runner_v83_13_16 import run_supervised_automation_runner

class Tests(unittest.TestCase):
    def write(self, p, v):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(v), encoding="utf-8")

    def case(self, execute=False, clear=False, active=False, risk=True, executor=None, max_cycles=3, max_failures=1):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        r = Path(t.name)
        self.write(r/"cycle.json", {"state":"CONTROLLED_CYCLE_READY"})
        self.write(r/"orch.json", {"state":"ORCHESTRATOR_ACTION_READY","recommended_action":"REFRESH_SCHEDULER_HEARTBEAT"})
        self.write(r/"disp.json", {"state":"LOCAL_ACTION_READY"})
        self.write(r/"risk.json", {"state":"SHADOW_RISK_CLEAR" if risk else "SHADOW_RISK_KILL_SWITCH_ACTIVE"})
        self.write(r/"policy.json", {
            "paper_only":True,"broker_write_enabled":False,"order_submission_enabled":False,
            "live_trading_enabled":False,"continuous_loop_enabled":False,
            "max_cycles_per_run":max_cycles,"max_consecutive_failures":max_failures,"pause_seconds":0
        })
        if active:
            self.write(r/"lock.json", {"active":True,"runner_id":"existing"})
        result = run_supervised_automation_runner(
            controlled_cycle_result_path=r/"cycle.json", orchestrator_result_path=r/"orch.json",
            dispatcher_result_path=r/"disp.json", risk_result_path=r/"risk.json",
            policy_path=r/"policy.json", runner_lock_path=r/"lock.json",
            runner_ledger_path=r/"ledger.jsonl", runner_summary_path=r/"summary.json",
            recovery_path=r/"recovery.json", dashboard_path=r/"dashboard.json",
            result_path=r/"result.json", execute_runner=execute, clear_runner_lock=clear,
            cycle_executor=executor,
        )
        return result, r

    def test_ready(self):
        x,_=self.case(); self.assertEqual(x["state"],"SUPERVISED_RUNNER_READY")
    def test_complete_bounded(self):
        x,r=self.case(execute=True); self.assertEqual(x["successful_cycles"],3); self.assertTrue((r/"summary.json").exists())
    def test_duplicate(self):
        x,_=self.case(execute=True,active=True); self.assertEqual(x["status"],"BLOCKED")
    def test_risk_gate(self):
        x,_=self.case(risk=False); self.assertEqual(x["state"],"SUPERVISED_RUNNER_SAFE_MODE")
    def test_failure_limit(self):
        f=lambda i:{"status":"BLOCKED","state":"CONTROLLED_CYCLE_RECOVERY_REQUIRED"}
        x,_=self.case(execute=True,executor=f,max_cycles=4,max_failures=2)
        self.assertEqual(x["attempted_cycles"],2); self.assertEqual(x["stop_reason"],"CONSECUTIVE_FAILURE_LIMIT_REACHED")
    def test_clear(self):
        x,_=self.case(clear=True,active=True); self.assertEqual(x["state"],"SUPERVISED_RUNNER_LOCK_CLEARED")
    def test_dashboard(self):
        x,r=self.case(); self.assertTrue(x["dashboard_state_written"]); self.assertTrue((r/"dashboard.json").exists())
    def test_summary_counts(self):
        n={"v":0}
        def mixed(i):
            n["v"]+=1
            return {"status":"BLOCKED","state":"CONTROLLED_CYCLE_RECOVERY_REQUIRED"} if n["v"]==2 else {"status":"PASS","state":"CONTROLLED_AUTOMATION_CYCLE_COMPLETE"}
        x,_=self.case(execute=True,executor=mixed,max_cycles=3,max_failures=2)
        self.assertEqual(x["successful_cycles"],2); self.assertEqual(x["failed_cycles"],1)
    def test_bounded_max(self):
        x,_=self.case(execute=True,max_cycles=2); self.assertEqual(x["attempted_cycles"],2)
    def test_safety(self):
        x,_=self.case(execute=True)
        self.assertTrue(x["operator_supervision_required"]); self.assertFalse(x["continuous_loop_enabled"])
        self.assertFalse(x["broker_write_enabled"]); self.assertEqual(x["actual_paper_orders_submitted"],0)

if __name__ == "__main__":
    unittest.main()
