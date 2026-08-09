from pathlib import Path
from datetime import datetime,timezone
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.daily_risk_budget_kill_switch_v2_1_29 import (
    DailyRiskBudgetKillSwitchV2129,
    DAILY_RISK_SESSION_CONFIRMATION,
)
from broker_integration_v1.daily_risk_budget_kill_switch_status_v2_1_29 import (
    build_v2_1_29_status,
)


def write_policy(root, *, max_trades=2, max_loss="5.00", max_consecutive=2):
    p=(
        Path(root)/"release"/
        "broker_integration_v2_1_29_daily_risk_budget_kill_switch"/
        "config"
    )
    p.mkdir(parents=True,exist_ok=True)
    path=p/"daily_risk_policy.json"
    path.write_text(json.dumps({
        "policy_name":"TEST",
        "max_completed_round_trips_per_day":max_trades,
        "max_daily_gross_loss_usd":max_loss,
        "max_consecutive_losses":max_consecutive,
        "pnl_source":"V2.1.27_FILL_BASED_GROSS_PNL_BEFORE_FEES",
    }),encoding="utf-8")
    return path


def append_trade(root, *, rid, pnl, completed_at="2026-08-10T15:00:00Z"):
    p=Path(root)/"runtime"/"final_round_trip_ledger_v2_1_27"
    p.mkdir(parents=True,exist_ok=True)
    row={
        "status":"COMPLETED_ALPACA_PAPER_ROUND_TRIP",
        "round_trip_id":rid,
        "symbol":"AAPL",
        "gross_pnl_from_fills":str(pnl),
        "completed_at_utc":completed_at,
        "pnl_semantics":"FILL_BASED_GROSS_PNL_BEFORE_FEES",
    }
    with (p/"completed_round_trips.jsonl").open("a",encoding="utf-8") as f:
        f.write(json.dumps(row)+"\n")


class FakeSession:
    def __init__(self, root, counter, pnl_sequence=None, abnormal=False, outside=False):
        self.root=Path(root)
        self.counter=counter
        self.pnl_sequence=list(pnl_sequence or [])
        self.abnormal=abnormal
        self.outside=outside

    def run(self, **kwargs):
        self.counter["calls"]+=1
        self.counter["max_completed"].append(
            kwargs["max_completed_round_trips"]
        )

        if self.abnormal:
            return {
                "status":"BROKEN_STATUS",
                "stop_reason":"BROKEN",
                "completed_round_trips_this_session":0,
                "new_completed_round_trip_ids":[],
            }

        if self.outside:
            return {
                "status":"PASS_CONTINUOUS_BOUNDED_PAPER_SESSION",
                "stop_reason":"WAITING_FOR_MARKET_SESSION",
                "completed_round_trips_this_session":0,
                "new_completed_round_trip_ids":[],
            }

        idx=self.counter["calls"]-1
        if idx < len(self.pnl_sequence):
            rid=f"rt-{idx+1}"
            append_trade(
                self.root,
                rid=rid,
                pnl=self.pnl_sequence[idx],
            )
            return {
                "status":"PASS_CONTINUOUS_BOUNDED_PAPER_SESSION",
                "stop_reason":"MAX_COMPLETED_ROUND_TRIPS_REACHED",
                "completed_round_trips_this_session":1,
                "new_completed_round_trip_ids":[rid],
            }

        return {
            "status":"PASS_CONTINUOUS_BOUNDED_PAPER_SESSION",
            "stop_reason":"MAX_SUPERVISOR_CYCLES",
            "completed_round_trips_this_session":0,
            "new_completed_round_trip_ids":[],
        }


class Tests(unittest.TestCase):
    def fixed_now(self):
        return datetime(2026,8,10,16,0,tzinfo=timezone.utc)

    def make(self,td,**kwargs):
        policy=write_policy(td,**kwargs)
        return DailyRiskBudgetKillSwitchV2129(
            td,
            config_path=policy,
            now_fn=self.fixed_now,
            sleep_fn=lambda _:None,
        )

    def test_no_trades_allows(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.make(td)
            r=c.evaluate()
            self.assertEqual(r["status"],"PASS_DAILY_RISK_BUDGET_ALLOW")
            self.assertTrue(r["trading_allowed"])
            self.assertEqual(r["completed_round_trips_today"],0)
            self.assertEqual(r["remaining_round_trips_today"],2)
            self.assertFalse(r["broker_network_used"])

    def test_daily_trade_cap_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.make(td)
            append_trade(td,rid="1",pnl="1.00")
            append_trade(td,rid="2",pnl="1.00")
            r=c.evaluate()
            self.assertFalse(r["trading_allowed"])
            self.assertIn("MAX_DAILY_ROUND_TRIPS_REACHED",r["block_reasons"])

    def test_daily_loss_budget_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.make(td,max_trades=5,max_loss="5.00",max_consecutive=5)
            append_trade(td,rid="1",pnl="-3.00")
            append_trade(td,rid="2",pnl="-2.25")
            r=c.evaluate()
            self.assertFalse(r["trading_allowed"])
            self.assertIn("MAX_DAILY_GROSS_LOSS_REACHED",r["block_reasons"])
            self.assertEqual(
                r["daily_fill_based_gross_pnl_before_fees"],
                "-5.25",
            )

    def test_consecutive_loss_guard_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.make(td,max_trades=5,max_loss="100",max_consecutive=2)
            append_trade(td,rid="1",pnl="2.00")
            append_trade(td,rid="2",pnl="-1.00")
            append_trade(td,rid="3",pnl="-1.00")
            r=c.evaluate()
            self.assertFalse(r["trading_allowed"])
            self.assertEqual(r["consecutive_losses"],2)
            self.assertIn("MAX_CONSECUTIVE_LOSSES_REACHED",r["block_reasons"])

    def test_manual_kill_switch_and_clear(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.make(td)
            e=c.engage_kill_switch("TEST_MANUAL_STOP")
            self.assertEqual(e["status"],"PASS_KILL_SWITCH_ENGAGED")
            blocked=c.evaluate()
            self.assertFalse(blocked["trading_allowed"])
            self.assertIn("TEST_MANUAL_STOP",blocked["block_reasons"])

            cleared=c.clear_kill_switch()
            self.assertEqual(cleared["status"],"PASS_KILL_SWITCH_CLEARED")
            allowed=c.evaluate()
            self.assertTrue(allowed["trading_allowed"])

    def test_paper_confirmation_required(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.make(td)
            r=c.run_guarded_session(
                mode="PAPER",
                confirmation="WRONG",
                max_supervisor_round_trips=1,
                interval_seconds=1,
            )
            self.assertEqual(
                r["status"],
                "BLOCKED_DAILY_RISK_SESSION_CONFIRMATION_REQUIRED",
            )

    def test_rechecks_after_each_trade_and_stops_at_cap(self):
        with tempfile.TemporaryDirectory() as td:
            policy=write_policy(
                td,max_trades=2,max_loss="100",max_consecutive=5
            )
            counter={"calls":0,"max_completed":[]}
            c=DailyRiskBudgetKillSwitchV2129(
                td,
                config_path=policy,
                session_factory=lambda:FakeSession(
                    td,counter,pnl_sequence=["1.00","1.00"]
                ),
                now_fn=self.fixed_now,
                sleep_fn=lambda _:None,
            )
            r=c.run_guarded_session(
                mode="PAPER",
                confirmation=DAILY_RISK_SESSION_CONFIRMATION,
                max_supervisor_round_trips=3,
                interval_seconds=1,
            )
            self.assertEqual(counter["calls"],2)
            self.assertEqual(counter["max_completed"],[1,1])
            self.assertEqual(
                r["stop_reason"],
                "POST_TRADE_DAILY_RISK_BLOCK",
            )
            self.assertFalse(
                r["final_risk_status"]["trading_allowed"]
            )
            self.assertEqual(
                r["final_risk_status"]["completed_round_trips_today"],
                2,
            )

    def test_loss_after_first_trade_blocks_second(self):
        with tempfile.TemporaryDirectory() as td:
            policy=write_policy(
                td,max_trades=5,max_loss="5.00",max_consecutive=5
            )
            counter={"calls":0,"max_completed":[]}
            c=DailyRiskBudgetKillSwitchV2129(
                td,
                config_path=policy,
                session_factory=lambda:FakeSession(
                    td,counter,pnl_sequence=["-5.50","3.00"]
                ),
                now_fn=self.fixed_now,
                sleep_fn=lambda _:None,
            )
            r=c.run_guarded_session(
                mode="PAPER",
                confirmation=DAILY_RISK_SESSION_CONFIRMATION,
                max_supervisor_round_trips=2,
                interval_seconds=1,
            )
            self.assertEqual(counter["calls"],1)
            self.assertEqual(
                r["stop_reason"],
                "POST_TRADE_DAILY_RISK_BLOCK",
            )
            self.assertIn(
                "MAX_DAILY_GROSS_LOSS_REACHED",
                r["final_risk_status"]["block_reasons"],
            )

    def test_abnormal_v2128_fail_closed_engages_kill(self):
        with tempfile.TemporaryDirectory() as td:
            policy=write_policy(td)
            counter={"calls":0,"max_completed":[]}
            c=DailyRiskBudgetKillSwitchV2129(
                td,
                config_path=policy,
                session_factory=lambda:FakeSession(
                    td,counter,abnormal=True
                ),
                now_fn=self.fixed_now,
                sleep_fn=lambda _:None,
            )
            r=c.run_guarded_session(
                mode="PAPER",
                confirmation=DAILY_RISK_SESSION_CONFIRMATION,
                max_supervisor_round_trips=1,
                interval_seconds=1,
            )
            self.assertEqual(
                r["stop_reason"],
                "ABNORMAL_SESSION_STATUS_KILL_SWITCH",
            )
            self.assertTrue(c._manual_kill_state()["engaged"])

    def test_outside_session_stops(self):
        with tempfile.TemporaryDirectory() as td:
            policy=write_policy(td)
            counter={"calls":0,"max_completed":[]}
            c=DailyRiskBudgetKillSwitchV2129(
                td,
                config_path=policy,
                session_factory=lambda:FakeSession(
                    td,counter,outside=True
                ),
                now_fn=self.fixed_now,
                sleep_fn=lambda _:None,
            )
            r=c.run_guarded_session(
                mode="DRY",
                max_supervisor_round_trips=2,
                interval_seconds=1,
            )
            self.assertEqual(
                r["stop_reason"],
                "WAITING_FOR_MARKET_SESSION",
            )
            self.assertEqual(counter["calls"],1)

    def test_status_contract(self):
        s=build_v2_1_29_status()
        self.assertTrue(s["v2_1_28_continuous_session_reused"])
        self.assertTrue(s["v2_1_27_completed_ledger_reused"])
        self.assertTrue(s["one_round_trip_per_delegated_call"])
        self.assertTrue(s["risk_rechecked_after_each_completed_round_trip"])
        self.assertTrue(s["daily_trade_cap"])
        self.assertTrue(s["daily_loss_budget"])
        self.assertTrue(s["consecutive_loss_guard"])
        self.assertTrue(s["manual_kill_switch"])
        self.assertFalse(s["new_entry_engine_created"])
        self.assertEqual(s["install_test_paper_orders"],0)
        self.assertFalse(s["live_trading_enabled"])


if __name__=="__main__":
    unittest.main()
