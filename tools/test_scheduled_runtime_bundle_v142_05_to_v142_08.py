import json, tempfile, unittest
from pathlib import Path
from autonomous_paper_runtime.scheduled_runtime_bundle import ScheduledRuntimeBundle

class Tests(unittest.TestCase):
    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def data(self):
        runtime = {
            "status":"PASS","state":"AUTONOMOUS_PAPER_RUNTIME_READY",
            "autonomous_paper_runtime_ready":True,
            "runtime_id":"runtime-001","session_id":"session-001",
            "safe_mode_engaged":False
        }
        token = {
            "runtime_id":"runtime-001","autonomous_paper_runtime_ready":True,
            "continuous_loop_enabled":False,"actual_submission_allowed":False,
            "broker_network_allowed":False,"live_trading_enabled":False
        }
        schedule = {
            "schedule_id":"schedule-001","enabled":True,"interval_seconds":60,
            "max_runs_per_invocation":1,"unbounded_scheduler":False,
            "actual_submission_allowed":False,"broker_network_allowed":False,
            "live_trading_enabled":False
        }
        resume = {
            "runtime_id":"runtime-001","session_id":"session-001",
            "last_completed_tick":1,"resume_state_verified":True
        }
        recovery = {
            "unresolved_order_state":False,"ledger_corrupted":False,
            "runtime_process_count":1,"recovery_verified":True,
            "heartbeat_age_seconds":5,"max_heartbeat_age_seconds":300,
            "restart_detected":False
        }
        emergency = {"engaged":False,"reason":""}
        return runtime, token, schedule, resume, recovery, emergency

    def run_case(self, values):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        names = ["runtime","token","schedule","resume","recovery","emergency"]
        paths = {name: root/f"{name}.json" for name in names}
        for name, value in zip(names, values):
            if value is not None:
                self.write(paths[name], value)
        result = ScheduledRuntimeBundle().run(
            runtime_result_path=paths["runtime"], runtime_token_path=paths["token"],
            schedule_policy_path=paths["schedule"], resume_snapshot_path=paths["resume"],
            recovery_snapshot_path=paths["recovery"], emergency_stop_path=paths["emergency"],
            scheduled_state_path=root/"state.json", heartbeat_path=root/"heartbeat.json",
            recovery_token_path=root/"recovery_token.json",
            scheduled_token_path=root/"scheduled_token.json", result_path=root/"result.json")
        return result, root

    def test_wait_before_runtime(self):
        values = list(self.data())
        values[0] = {"status":"PASS","state":"WAIT_PAPER_PRODUCTION_RELEASE","autonomous_paper_runtime_ready":False,"safe_mode_engaged":False}
        result,_ = self.run_case(values)
        self.assertEqual(result["state"], "WAIT_AUTONOMOUS_PAPER_RUNTIME")

    def test_schedule_ready(self):
        result,root = self.run_case(self.data())
        self.assertEqual(result["state"], "AUTONOMOUS_RUNTIME_SCHEDULE_READY")
        self.assertEqual(result["next_tick"], 2)
        self.assertTrue((root/"scheduled_token.json").exists())

    def test_emergency_stop_blocks(self):
        values=list(self.data()); values[5]={"engaged":True,"reason":"manual"}
        result,_=self.run_case(values)
        self.assertEqual(result["state"], "SCHEDULED_RUNTIME_EMERGENCY_STOP")

    def test_unbounded_scheduler_blocks(self):
        values=list(self.data()); values[2]=dict(values[2]); values[2]["unbounded_scheduler"]=True
        result,_=self.run_case(values)
        self.assertEqual(result["status"], "BLOCKED")

    def test_resume_mismatch_blocks(self):
        values=list(self.data()); values[3]=dict(values[3]); values[3]["runtime_id"]="wrong"
        result,_=self.run_case(values)
        self.assertEqual(result["status"], "BLOCKED")

    def test_recovery_unresolved_order_blocks(self):
        values=list(self.data()); values[4]=dict(values[4]); values[4]["unresolved_order_state"]=True
        result,_=self.run_case(values)
        self.assertEqual(result["status"], "BLOCKED")

if __name__=="__main__":
    unittest.main()
