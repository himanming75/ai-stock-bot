from pathlib import Path
from datetime import datetime,timezone
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.daily_performance_operation_report_v2_1_32 import (
    DailyPerformanceOperationReportV2132,
)
from broker_integration_v1.daily_performance_operation_report_status_v2_1_32 import (
    build_v2_1_32_status,
)


def append_jsonl(path,row):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f:
        f.write(json.dumps(row)+"\n")


class Tests(unittest.TestCase):
    def fixed_now(self):
        return datetime(2026,8,10,22,0,tzinfo=timezone.utc)

    def make(self,td):
        return DailyPerformanceOperationReportV2132(
            td,
            now_fn=self.fixed_now,
        )

    def test_empty_day_report(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.make(td)
            r=c.build("2026-08-10")
            self.assertEqual(
                r["status"],
                "PASS_DAILY_PERFORMANCE_OPERATION_REPORT",
            )
            self.assertEqual(
                r["trade_performance"]["completed_round_trips"],
                0,
            )
            self.assertEqual(
                r["trade_performance"]["fill_based_gross_pnl_before_fees"],
                "0",
            )
            self.assertFalse(r["validation_day"]["eligible"])
            self.assertFalse(r["broker_network_used"])
            self.assertEqual(r["paper_orders_submitted"],0)

    def test_trade_performance_aggregates_existing_v2127_values(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.make(td)
            append_jsonl(c.completed_ledger,{
                "status":"COMPLETED_ALPACA_PAPER_ROUND_TRIP",
                "round_trip_id":"rt-1",
                "symbol":"AAPL",
                "gross_pnl_from_fills":"2.50",
                "return_pct_from_fills":"1.25",
                "holding_seconds":600,
                "exit":{"reason":"TAKE_PROFIT"},
                "completed_at_utc":"2026-08-10T15:00:00Z",
            })
            append_jsonl(c.completed_ledger,{
                "status":"COMPLETED_ALPACA_PAPER_ROUND_TRIP",
                "round_trip_id":"rt-2",
                "symbol":"MSFT",
                "gross_pnl_from_fills":"-1.00",
                "return_pct_from_fills":"-0.50",
                "holding_seconds":300,
                "exit":{"reason":"STOP_LOSS"},
                "completed_at_utc":"2026-08-10T16:00:00Z",
            })
            r=c.build("2026-08-10")
            t=r["trade_performance"]
            self.assertEqual(t["completed_round_trips"],2)
            self.assertEqual(t["wins"],1)
            self.assertEqual(t["losses"],1)
            self.assertEqual(t["fill_based_gross_pnl_before_fees"],"1.50")
            self.assertEqual(t["average_return_pct_from_fills"],"0.375")
            self.assertEqual(t["average_holding_seconds"],450.0)
            self.assertEqual(t["best_trade"]["round_trip_id"],"rt-1")
            self.assertEqual(t["worst_trade"]["round_trip_id"],"rt-2")
            self.assertEqual(t["exit_reasons"]["STOP_LOSS"],1)
            self.assertEqual(t["exit_reasons"]["TAKE_PROFIT"],1)

    def test_latest_risk_card(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.make(td)
            append_jsonl(c.risk_ledger,{
                "status":"PASS_DAILY_RISK_BUDGET_ALLOW",
                "market_date":"2026-08-10",
                "trading_allowed":True,
                "block_reasons":[],
                "completed_round_trips_today":1,
                "daily_fill_based_gross_pnl_before_fees":"2.50",
                "daily_gross_loss_budget_used_usd":"0",
                "consecutive_losses":0,
                "remaining_round_trips_today":1,
                "remaining_daily_gross_loss_budget_usd":"5.00",
                "manual_kill_switch":{"engaged":False},
            })
            r=c.build("2026-08-10")
            self.assertTrue(r["risk"]["trading_allowed"])
            self.assertEqual(r["risk"]["remaining_round_trips_today"],1)

    def test_recovery_and_operation_counts(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.make(td)
            append_jsonl(c.recovery_ledger,{
                "status":"PASS_RECOVERY_RECONCILIATION",
                "recovery_action":"IDLE_START",
                "broker_network_used":True,
                "broker_snapshot":{
                    "observed_at_utc":"2026-08-10T13:00:00Z"
                },
            })
            append_jsonl(c.recovery_ledger,{
                "status":"BLOCKED_RECOVERY_STATE_MISMATCH",
                "recovery_action":"FAIL_CLOSED",
                "broker_network_used":True,
                "broker_snapshot":{
                    "observed_at_utc":"2026-08-10T14:00:00Z"
                },
            })
            append_jsonl(c.operation_ledger,{
                "status":"PASS_ONE_CLICK_DAILY_PAPER_OPERATION",
                "started_at_utc":"2026-08-10T13:20:00Z",
                "ended_at_utc":"2026-08-10T20:00:00Z",
            })
            r=c.build("2026-08-10")
            self.assertEqual(r["recovery_operations"]["events"],2)
            self.assertEqual(r["recovery_operations"]["blocked_events"],1)
            self.assertEqual(r["daily_operation"]["successful_paper_operations"],1)
            self.assertTrue(r["validation_day"]["eligible"])

    def test_validation_day_dedup(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.make(td)
            append_jsonl(c.operation_ledger,{
                "status":"PASS_ONE_CLICK_DAILY_PAPER_OPERATION",
                "started_at_utc":"2026-08-10T13:20:00Z",
                "ended_at_utc":"2026-08-10T20:00:00Z",
            })
            r1=c.build("2026-08-10")
            r2=c.build("2026-08-10")
            self.assertTrue(r1["validation_day"]["new_validation_ledger_row"])
            self.assertFalse(r2["validation_day"]["new_validation_ledger_row"])
            rows=c._jsonl(c.validation_ledger)
            self.assertEqual(len(rows),1)

    def test_validation_progress_counts_prior_operation_dates(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.make(td)
            append_jsonl(c.operation_ledger,{
                "status":"PASS_ONE_CLICK_DAILY_PAPER_OPERATION",
                "started_at_utc":"2026-08-07T13:20:00Z",
                "ended_at_utc":"2026-08-07T20:00:00Z",
            })
            append_jsonl(c.operation_ledger,{
                "status":"PASS_ONE_CLICK_DAILY_PAPER_OPERATION",
                "started_at_utc":"2026-08-10T13:20:00Z",
                "ended_at_utc":"2026-08-10T20:00:00Z",
            })
            r=c.build("2026-08-10")
            self.assertEqual(
                r["validation_day"]["qualified_validation_days_total"],
                2,
            )
            self.assertEqual(
                r["validation_day"]["remaining_to_target"],
                8,
            )

    def test_markdown_and_json_files_created(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.make(td)
            r=c.build("2026-08-10")
            self.assertTrue(
                (c.report_dir/"2026-08-10_daily_report.json").exists()
            )
            self.assertTrue(
                (c.report_dir/"2026-08-10_daily_report.md").exists()
            )
            self.assertTrue(c.latest_json.exists())
            self.assertTrue(c.latest_md.exists())
            md=c.latest_md.read_text(encoding="utf-8")
            self.assertIn("Daily Paper Performance",md)
            self.assertIn("Validation Progress",md)

    def test_status_contract(self):
        s=build_v2_1_32_status()
        self.assertTrue(s["v2_1_27_completed_round_trip_ledger_reused"])
        self.assertTrue(s["v2_1_29_risk_ledger_reused"])
        self.assertTrue(s["v2_1_30_recovery_ledger_reused"])
        self.assertTrue(s["v2_1_31_operation_ledger_reused"])
        self.assertFalse(s["pnl_recomputed_from_prices"])
        self.assertTrue(s["v2_1_27_fill_based_pnl_aggregated"])
        self.assertTrue(s["json_daily_report"])
        self.assertTrue(s["markdown_daily_report"])
        self.assertTrue(s["validation_day_ledger"])
        self.assertFalse(s["new_execution_logic_created"])
        self.assertFalse(s["broker_network_used"])
        self.assertEqual(s["install_test_paper_orders"],0)
        self.assertFalse(s["live_trading_enabled"])


if __name__=="__main__":
    unittest.main()
