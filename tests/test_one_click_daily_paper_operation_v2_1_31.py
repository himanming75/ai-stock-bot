from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.one_click_daily_paper_operation_v2_1_31 import (
    OneClickDailyPaperOperationV2131,
    DAILY_OPERATION_CONFIRMATION,
)
from broker_integration_v1.one_click_daily_paper_operation_status_v2_1_31 import (
    build_v2_1_31_status,
)


def write_policy(root, **overrides):
    p=(
        Path(root)/"release"/
        "broker_integration_v2_1_31_one_click_daily_paper_operation"/
        "config"
    )
    p.mkdir(parents=True,exist_ok=True)
    row={
        "policy_name":"TEST",
        "market_wait_poll_seconds":1,
        "max_market_wait_seconds":10,
        "max_round_trips":2,
        "session_interval_seconds":1,
        "paper_only":True,
        "live_trading":False,
    }
    row.update(overrides)
    path=p/"daily_operation_policy.json"
    path.write_text(json.dumps(row),encoding="utf-8")
    return path


def append_completed(root,rid):
    p=Path(root)/"runtime"/"final_round_trip_ledger_v2_1_27"
    p.mkdir(parents=True,exist_ok=True)
    with (p/"completed_round_trips.jsonl").open("a",encoding="utf-8") as f:
        f.write(json.dumps({
            "status":"COMPLETED_ALPACA_PAPER_ROUND_TRIP",
            "round_trip_id":rid,
        })+"\n")


class FakeRisk:
    def __init__(self,allowed=True):
        self.allowed=allowed
        self.kills=[]
        self.eval_calls=0

    def evaluate(self):
        self.eval_calls+=1
        return {
            "status":(
                "PASS_DAILY_RISK_BUDGET_ALLOW"
                if self.allowed
                else "BLOCKED_BY_DAILY_RISK_OR_KILL_SWITCH"
            ),
            "trading_allowed":self.allowed,
            "block_reasons":[] if self.allowed else ["TEST_BLOCK"],
            "completed_round_trips_today":0,
        }

    def engage_kill_switch(self,reason):
        self.kills.append(reason)
        return {"status":"PASS_KILL_SWITCH_ENGAGED"}


class FakeRecovery:
    def __init__(
        self,
        *,
        startup_ok=True,
        clocks=None,
        delegated_status="PASS_RECOVERY_RESUMED_EXISTING_V2_1_29",
        delegated_stop="WAITING_FOR_MARKET_SESSION",
        root=None,
        add_completed=None,
    ):
        self.startup_ok=startup_ok
        self.clocks=list(clocks or [True])
        self.snap_calls=0
        self.run_calls=0
        self.root=root
        self.add_completed=add_completed

    def local_plan(self):
        return {
            "status":"PASS_LOCAL_RECOVERY_PLAN",
            "recovery_action":"IDLE_START",
            "broker_network_used":False,
        }

    def reconcile(self):
        if not self.startup_ok:
            return {
                "status":"BLOCKED_RECOVERY_STATE_MISMATCH",
                "recovery_action":"FAIL_CLOSED",
            }
        return {
            "status":"PASS_RECOVERY_RECONCILIATION",
            "recovery_action":"IDLE_START",
        }

    def acquire_broker_snapshot(self):
        idx=min(self.snap_calls,len(self.clocks)-1)
        is_open=self.clocks[idx]
        self.snap_calls+=1
        return {
            "status":"PASS_PAPER_BROKER_RECOVERY_SNAPSHOT",
            "snapshot":{
                "clock":{
                    "is_open":is_open,
                    "next_open":"2026-08-10T13:30:00Z",
                    "next_close":"2026-08-10T20:00:00Z",
                }
            }
        }

    def recover_and_resume(self,**kwargs):
        self.run_calls+=1
        if self.root and self.add_completed:
            append_completed(self.root,self.add_completed)
        return {
            "status":"PASS_RECOVERY_RESUMED_EXISTING_V2_1_29",
            "delegated_stop_reason":"MAX_COMPLETED_ROUND_TRIPS_REACHED",
        }


class Clock:
    def __init__(self):
        self.t=datetime(2026,8,10,12,0,tzinfo=timezone.utc)
    def now(self):
        return self.t
    def sleep(self,seconds):
        self.t+=timedelta(seconds=seconds)


class Tests(unittest.TestCase):
    def test_dry_plan_no_broker_network(self):
        with tempfile.TemporaryDirectory() as td:
            policy=write_policy(td)
            risk=FakeRisk(True)
            rec=FakeRecovery()
            c=OneClickDailyPaperOperationV2131(
                td,
                recovery_factory=lambda:rec,
                risk_factory=lambda:risk,
                config_path=policy,
            )
            r=c.dry_plan()
            self.assertEqual(r["status"],"PASS_ONE_CLICK_DAILY_DRY_PLAN")
            self.assertFalse(r["broker_network_used"])
            self.assertFalse(r["broker_write_performed"])
            self.assertEqual(rec.run_calls,0)

    def test_dry_plan_blocks_on_risk(self):
        with tempfile.TemporaryDirectory() as td:
            policy=write_policy(td)
            risk=FakeRisk(False)
            c=OneClickDailyPaperOperationV2131(
                td,
                recovery_factory=lambda:FakeRecovery(),
                risk_factory=lambda:risk,
                config_path=policy,
            )
            r=c.dry_plan()
            self.assertEqual(r["status"],"BLOCKED_ONE_CLICK_DAILY_DRY_PLAN")
            self.assertFalse(r["would_delegate_to_v2_1_30"])

    def test_confirmation_required(self):
        with tempfile.TemporaryDirectory() as td:
            c=OneClickDailyPaperOperationV2131(
                td,
                config_path=write_policy(td),
            )
            r=c.run_paper(confirmation="WRONG")
            self.assertEqual(
                r["status"],
                "BLOCKED_DAILY_OPERATION_CONFIRMATION_REQUIRED",
            )

    def test_startup_recovery_failure_engages_existing_kill(self):
        with tempfile.TemporaryDirectory() as td:
            risk=FakeRisk(True)
            rec=FakeRecovery(startup_ok=False)
            c=OneClickDailyPaperOperationV2131(
                td,
                recovery_factory=lambda:rec,
                risk_factory=lambda:risk,
                config_path=write_policy(td),
            )
            r=c.run_paper(
                confirmation=DAILY_OPERATION_CONFIRMATION
            )
            self.assertEqual(
                r["status"],
                "BLOCKED_DAILY_OPERATION_STARTUP_RECOVERY",
            )
            self.assertEqual(
                risk.kills,
                ["V2_1_31_STARTUP_RECOVERY_FAIL_CLOSED"],
            )
            self.assertEqual(rec.run_calls,0)

    def test_pre_risk_blocks_before_market_wait(self):
        with tempfile.TemporaryDirectory() as td:
            risk=FakeRisk(False)
            rec=FakeRecovery()
            c=OneClickDailyPaperOperationV2131(
                td,
                recovery_factory=lambda:rec,
                risk_factory=lambda:risk,
                config_path=write_policy(td),
            )
            r=c.run_paper(
                confirmation=DAILY_OPERATION_CONFIRMATION
            )
            self.assertEqual(
                r["status"],
                "BLOCKED_DAILY_OPERATION_PRE_RISK",
            )
            self.assertEqual(rec.snap_calls,0)
            self.assertEqual(rec.run_calls,0)

    def test_waits_until_market_open_then_delegates_once(self):
        with tempfile.TemporaryDirectory() as td:
            clock=Clock()
            risk=FakeRisk(True)
            rec=FakeRecovery(
                clocks=[False,False,True],
                root=td,
                add_completed="rt-new",
            )
            c=OneClickDailyPaperOperationV2131(
                td,
                recovery_factory=lambda:rec,
                risk_factory=lambda:risk,
                config_path=write_policy(
                    td,
                    market_wait_poll_seconds=1,
                    max_market_wait_seconds=10,
                ),
                now_fn=clock.now,
                sleep_fn=clock.sleep,
            )
            r=c.run_paper(
                confirmation=DAILY_OPERATION_CONFIRMATION
            )
            self.assertEqual(
                r["status"],
                "PASS_ONE_CLICK_DAILY_PAPER_OPERATION",
            )
            self.assertEqual(rec.snap_calls,3)
            self.assertEqual(rec.run_calls,1)
            self.assertEqual(r["new_completed_round_trip_count"],1)
            self.assertEqual(
                r["new_completed_round_trip_ids"],
                ["rt-new"],
            )
            self.assertEqual(r["live_orders_submitted"],0)

    def test_market_wait_timeout_no_trading_delegation(self):
        with tempfile.TemporaryDirectory() as td:
            clock=Clock()
            risk=FakeRisk(True)
            rec=FakeRecovery(clocks=[False])
            c=OneClickDailyPaperOperationV2131(
                td,
                recovery_factory=lambda:rec,
                risk_factory=lambda:risk,
                config_path=write_policy(
                    td,
                    market_wait_poll_seconds=2,
                    max_market_wait_seconds=4,
                ),
                now_fn=clock.now,
                sleep_fn=clock.sleep,
            )
            r=c.run_paper(
                confirmation=DAILY_OPERATION_CONFIRMATION
            )
            self.assertEqual(
                r["status"],
                "STOPPED_MARKET_WAIT_TIMEOUT",
            )
            self.assertEqual(rec.run_calls,0)

    def test_status_contract(self):
        s=build_v2_1_31_status()
        self.assertTrue(s["v2_1_30_operational_entry_reused"])
        self.assertTrue(s["v2_1_29_daily_risk_reused"])
        self.assertTrue(s["market_open_wait_read_only"])
        self.assertTrue(s["startup_recovery_before_wait"])
        self.assertFalse(s["new_signal_engine_created"])
        self.assertFalse(s["new_trading_state_machine_created"])
        self.assertEqual(s["install_test_paper_orders"],0)
        self.assertFalse(s["live_trading_enabled"])


if __name__=="__main__":
    unittest.main()
