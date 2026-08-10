from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.one_click_daily_paper_operation_v2_1_31 import (
    OneClickDailyPaperOperationV2131, DAILY_OPERATION_CONFIRMATION,
)
from broker_integration_v1.market_open_transition_repair_status_v2_1_31_2 import (
    build_v2_1_31_2_status,
)

def write_policy(root, **overrides):
    p=Path(root)/"release"/"broker_integration_v2_1_31_one_click_daily_paper_operation"/"config"
    p.mkdir(parents=True,exist_ok=True)
    row={"policy_name":"TEST","market_wait_poll_seconds":1,"max_market_wait_seconds":20,
         "market_wait_broker_failure_grace_seconds":5,"max_round_trips":2,
         "session_interval_seconds":1,"paper_only":True,"live_trading":False}
    row.update(overrides)
    path=p/"daily_operation_policy.json"
    path.write_text(json.dumps(row),encoding="utf-8")
    return path

class Clock:
    def __init__(self): self.t=datetime(2026,8,10,13,20,tzinfo=timezone.utc)
    def now(self): return self.t
    def sleep(self,seconds): self.t+=timedelta(seconds=seconds)

class Risk:
    def __init__(self,sequence=None):
        self.sequence=list(sequence or [True,True,True]); self.calls=0; self.kills=[]
    def evaluate(self):
        idx=min(self.calls,len(self.sequence)-1); allowed=self.sequence[idx]; self.calls+=1
        return {"status":"PASS_DAILY_RISK_BUDGET_ALLOW" if allowed else "BLOCKED_BY_DAILY_RISK_OR_KILL_SWITCH",
                "trading_allowed":allowed,"block_reasons":[] if allowed else ["TEST_BLOCK"]}
    def engage_kill_switch(self,reason): self.kills.append(reason); return {"status":"PASS_KILL_SWITCH_ENGAGED"}

class Recovery:
    def __init__(self,snapshots,*,reconcile_sequence=None):
        self.snapshots=list(snapshots); self.snap_calls=0; self.run_calls=0
        self.reconcile_sequence=list(reconcile_sequence or [True,True,True]); self.reconcile_calls=0
    def local_plan(self): return {"status":"PASS_LOCAL_RECOVERY_PLAN","recovery_action":"IDLE_START"}
    def reconcile(self):
        idx=min(self.reconcile_calls,len(self.reconcile_sequence)-1); ok=self.reconcile_sequence[idx]; self.reconcile_calls+=1
        return {"status":"PASS_RECOVERY_RECONCILIATION" if ok else "BLOCKED_RECOVERY_STATE_MISMATCH",
                "recovery_action":"IDLE_START" if ok else "FAIL_CLOSED"}
    def acquire_broker_snapshot(self):
        idx=min(self.snap_calls,len(self.snapshots)-1); item=self.snapshots[idx]; self.snap_calls+=1
        if item=="FAIL": return {"status":"BLOCKED_BROKER_READ_RETRIES_EXHAUSTED","errors":[{"error":"temporary"}]}
        return {"status":"PASS_PAPER_BROKER_RECOVERY_SNAPSHOT","snapshot":{"clock":{"is_open":bool(item),
                "next_open":"2026-08-10T09:30:00-04:00","next_close":"2026-08-10T16:00:00-04:00"}}}
    def recover_and_resume(self,**kwargs):
        self.run_calls+=1
        return {"status":"PASS_RECOVERY_RESUMED_EXISTING_V2_1_29","delegated_stop_reason":"TEST_COMPLETE"}

class Tests(unittest.TestCase):
    def test_transient_failure_continues_to_open(self):
        with tempfile.TemporaryDirectory() as td:
            clock=Clock(); risk=Risk(); rec=Recovery(["FAIL",False,True])
            c=OneClickDailyPaperOperationV2131(td,recovery_factory=lambda:rec,risk_factory=lambda:risk,
                    sleep_fn=clock.sleep,now_fn=clock.now,config_path=write_policy(td))
            r=c.run_paper(confirmation=DAILY_OPERATION_CONFIRMATION)
            self.assertEqual(r["status"],"PASS_ONE_CLICK_DAILY_PAPER_OPERATION")
            self.assertEqual(rec.run_calls,1)
            self.assertEqual(r["market_wait_broker_failure_events"],1)
            self.assertEqual(r["post_open_recovery_status"],"PASS_RECOVERY_RECONCILIATION")

    def test_persistent_outage_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            clock=Clock(); risk=Risk(); rec=Recovery(["FAIL"])
            c=OneClickDailyPaperOperationV2131(td,recovery_factory=lambda:rec,risk_factory=lambda:risk,
                    sleep_fn=clock.sleep,now_fn=clock.now,
                    config_path=write_policy(td,market_wait_broker_failure_grace_seconds=2))
            r=c.run_paper(confirmation=DAILY_OPERATION_CONFIRMATION)
            self.assertEqual(r["status"],"BLOCKED_MARKET_WAIT_BROKER_UNAVAILABLE")
            self.assertEqual(rec.run_calls,0)
            self.assertGreaterEqual(r["market_wait"]["broker_failure_elapsed_seconds"],2)

    def test_open_recovery_recheck_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            clock=Clock(); risk=Risk(); rec=Recovery([True],reconcile_sequence=[True,False])
            c=OneClickDailyPaperOperationV2131(td,recovery_factory=lambda:rec,risk_factory=lambda:risk,
                    sleep_fn=clock.sleep,now_fn=clock.now,config_path=write_policy(td))
            r=c.run_paper(confirmation=DAILY_OPERATION_CONFIRMATION)
            self.assertEqual(r["status"],"BLOCKED_MARKET_OPEN_RECOVERY_RECHECK")
            self.assertEqual(rec.run_calls,0)
            self.assertEqual(risk.kills,["V2_1_31_2_MARKET_OPEN_RECOVERY_RECHECK_FAIL_CLOSED"])

    def test_open_risk_recheck_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            clock=Clock(); risk=Risk([True,False]); rec=Recovery([True])
            c=OneClickDailyPaperOperationV2131(td,recovery_factory=lambda:rec,risk_factory=lambda:risk,
                    sleep_fn=clock.sleep,now_fn=clock.now,config_path=write_policy(td))
            r=c.run_paper(confirmation=DAILY_OPERATION_CONFIRMATION)
            self.assertEqual(r["status"],"BLOCKED_MARKET_OPEN_RISK_RECHECK")
            self.assertEqual(rec.run_calls,0)

    def test_status(self):
        s=build_v2_1_31_2_status()
        self.assertTrue(s["overnight_wait_continues_after_transient_failure"])
        self.assertTrue(s["market_open_recovery_recheck"])
        self.assertTrue(s["market_open_risk_recheck"])
        self.assertTrue(s["persistent_broker_outage_fail_closed"])
        self.assertEqual(s["install_test_paper_orders"],0)
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__": unittest.main()
