from pathlib import Path
from datetime import datetime,timezone
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.final_exit_fill_reconciliation_round_trip_ledger_v2_1_27 import (
    FinalExitFillReconciliationRoundTripLedgerV2127,
)
from broker_integration_v1.final_exit_fill_reconciliation_round_trip_status_v2_1_27 import (
    build_v2_1_27_status,
)


def write_sources(root):
    root=Path(root)

    p23=(
        root/"runtime"/"alpaca_paper_order_position_lifecycle_v2_1_23"
    )
    p25=(
        root/"runtime"/"alpaca_paper_exit_recovery_v2_1_25"
    )
    p26=(
        root/"runtime"/"full_alpaca_paper_round_trip_v2_1_26"
    )
    for p in (p23,p25,p26):
        p.mkdir(parents=True,exist_ok=True)

    entry={
        "status":"PASS_ORDER_POSITION_LIFECYCLE_READ_ONLY",
        "evidence_key":"ev-001",
        "client_order_id":"entry-client-1",
        "selected_candidate":{
            "symbol":"AAPL",
            "side":"buy",
        },
        "order_lifecycle_summary":{
            "status":"PASS",
            "final_status":"filled",
            "final_snapshot":{
                "client_order_id":"entry-client-1",
                "broker_order_id":"entry-broker-1",
                "symbol":"AAPL",
                "side":"buy",
                "status":"filled",
                "filled_qty":"0.25",
                "filled_avg_price":"100.00",
                "submitted_at":"2026-08-10T14:30:00Z",
                "filled_at":"2026-08-10T14:30:02Z",
                "position_found":True,
                "position":{
                    "symbol":"AAPL",
                    "qty":"0.25",
                    "avg_entry_price":"100.00",
                },
            },
        },
        "position_lifecycle_state":"POSITION_EXIT_READY_READ_ONLY",
        "position_exit_decision":{
            "action":"EXIT",
            "reason":"TAKE_PROFIT",
        },
    }
    (p23/"latest_lifecycle.json").write_text(
        json.dumps(entry),
        encoding="utf-8",
    )

    exit_row={
        "status":"PAPER_EXIT_ORDER_SUBMITTED_ONCE",
        "evidence_key":"ev-001",
        "symbol":"AAPL",
        "entry_client_order_id":"entry-client-1",
        "exit_reason":"TAKE_PROFIT",
        "exit_fingerprint_sha256":"exit-fp-001",
        "paper_exit_order_submitted":True,
        "live_order_submitted":False,
        "exit_order":{
            "id":"exit-broker-1",
            "client_order_id":"exit-client-1",
            "symbol":"AAPL",
            "side":"sell",
            "status":"accepted",
            "paper":True,
        },
        "submitted_at_utc":"2026-08-10T15:00:00Z",
    }
    (p25/"exit_ledger.jsonl").write_text(
        json.dumps(exit_row)+"\n",
        encoding="utf-8",
    )

    state={
        "version":"V2.1.26",
        "phase":"ROUND_TRIP_EXIT_SUBMITTED",
        "evidence_key":"ev-001",
        "symbol":"AAPL",
        "entry_submitted":True,
        "entry_client_order_id":"entry-client-1",
        "position_observed":True,
        "exit_ready":True,
        "exit_submitted":True,
        "round_trip_complete":False,
        "paper_entry_count":1,
        "paper_exit_count":1,
        "live_order_count":0,
    }
    (p26/"cycle_state.json").write_text(
        json.dumps(state),
        encoding="utf-8",
    )


class FakeClient:
    def __init__(
        self,
        *,
        status="filled",
        position_after=False,
        broker_order_id="exit-broker-1",
        filled_qty="0.25",
        filled_avg_price="110.00",
    ):
        self.status=status
        self.position_after=position_after
        self.broker_order_id=broker_order_id
        self.filled_qty=filled_qty
        self.filled_avg_price=filled_avg_price
        self.order_calls=0

    def get_order_by_client_id(self,client_order_id):
        self.order_calls+=1
        return {
            "id":self.broker_order_id,
            "client_order_id":client_order_id,
            "symbol":"AAPL",
            "side":"sell",
            "type":"market",
            "status":self.status,
            "qty":"0.25",
            "filled_qty":self.filled_qty,
            "filled_avg_price":self.filled_avg_price,
            "submitted_at":"2026-08-10T15:00:00Z",
            "filled_at":"2026-08-10T15:00:03Z" if self.status=="filled" else None,
        }

    def get_positions(self):
        if not self.position_after:
            return []
        return [{
            "symbol":"AAPL",
            "qty":"0.05",
            "avg_entry_price":"100.00",
            "current_price":"110.00",
        }]

    def get_account(self):
        return {
            "equity":"100025.00",
            "cash":"100000.00",
        }

    def get_clock(self):
        return {"is_open":True}


class Tests(unittest.TestCase):
    def fixed_now(self):
        return datetime(2026,8,10,15,0,5,tzinfo=timezone.utc)

    def test_waits_without_sources_no_network(self):
        with tempfile.TemporaryDirectory() as td:
            c=FinalExitFillReconciliationRoundTripLedgerV2127(td)
            r=c.build_plan()
            self.assertEqual(
                r["status"],
                "WAITING_FOR_V2_1_23_ENTRY_LIFECYCLE",
            )
            self.assertFalse(r["broker_network_used"])

    def test_ready_plan_no_network(self):
        with tempfile.TemporaryDirectory() as td:
            write_sources(td)
            c=FinalExitFillReconciliationRoundTripLedgerV2127(td)
            r=c.build_plan()
            self.assertEqual(
                r["status"],
                "READY_FOR_READ_ONLY_EXIT_FILL_RECONCILIATION",
            )
            self.assertEqual(r["symbol"],"AAPL")
            self.assertEqual(r["exit_client_order_id"],"exit-client-1")
            self.assertFalse(r["broker_network_used"])

    def test_filled_exit_completes_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            write_sources(td)
            fake=FakeClient()
            c=FinalExitFillReconciliationRoundTripLedgerV2127(
                td,
                client_factory=lambda:fake,
                sleep_fn=lambda _:None,
                now_fn=self.fixed_now,
            )
            r=c.reconcile(interval_seconds=1,max_cycles=2)

            self.assertEqual(
                r["status"],
                "PASS_FINAL_EXIT_FILL_RECONCILIATION",
            )
            completed=r["completed_round_trip"]
            self.assertEqual(
                completed["status"],
                "COMPLETED_ALPACA_PAPER_ROUND_TRIP",
            )
            self.assertEqual(
                completed["gross_pnl_from_fills"],
                "2.5000",
            )
            self.assertEqual(
                completed["return_pct_from_fills"],
                "10.0",
            )
            self.assertEqual(
                completed["holding_seconds"],
                1801.0,
            )
            self.assertTrue(
                completed["quantity_reconciliation"]["exact_match"]
            )
            self.assertFalse(completed["fees_included"])
            self.assertEqual(
                completed["pnl_semantics"],
                "FILL_BASED_GROSS_PNL_BEFORE_FEES",
            )
            self.assertEqual(
                r["paper_orders_submitted"],
                0,
            )
            self.assertFalse(r["broker_write_performed"])

            state=json.loads(
                (
                    Path(td)/"runtime"/
                    "full_alpaca_paper_round_trip_v2_1_26"/
                    "cycle_state.json"
                ).read_text()
            )
            self.assertTrue(state["round_trip_complete"])
            self.assertTrue(state["final_fill_reconciled"])
            self.assertEqual(state["phase"],"ROUND_TRIP_COMPLETE")

    def test_duplicate_completed_round_trip_blocked_locally(self):
        with tempfile.TemporaryDirectory() as td:
            write_sources(td)
            fake=FakeClient()
            c=FinalExitFillReconciliationRoundTripLedgerV2127(
                td,
                client_factory=lambda:fake,
                sleep_fn=lambda _:None,
                now_fn=self.fixed_now,
            )
            first=c.reconcile(interval_seconds=1,max_cycles=1)
            self.assertEqual(
                first["status"],
                "PASS_FINAL_EXIT_FILL_RECONCILIATION",
            )
            calls=fake.order_calls

            second=c.build_plan()
            self.assertEqual(
                second["status"],
                "ROUND_TRIP_ALREADY_COMPLETED_NO_DUPLICATE",
            )
            self.assertEqual(fake.order_calls,calls)

    def test_position_remaining_blocks_completion(self):
        with tempfile.TemporaryDirectory() as td:
            write_sources(td)
            fake=FakeClient(position_after=True)
            c=FinalExitFillReconciliationRoundTripLedgerV2127(
                td,
                client_factory=lambda:fake,
                sleep_fn=lambda _:None,
                now_fn=self.fixed_now,
            )
            r=c.reconcile(interval_seconds=1,max_cycles=1)
            self.assertEqual(
                r["status"],
                "BLOCKED_EXIT_FILLED_BUT_POSITION_REMAINS",
            )
            completed=(
                Path(td)/"runtime"/"final_round_trip_ledger_v2_1_27"/
                "completed_round_trips.jsonl"
            )
            self.assertFalse(completed.exists())

    def test_broker_order_id_mismatch_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            write_sources(td)
            fake=FakeClient(broker_order_id="WRONG")
            c=FinalExitFillReconciliationRoundTripLedgerV2127(
                td,
                client_factory=lambda:fake,
                sleep_fn=lambda _:None,
                now_fn=self.fixed_now,
            )
            r=c.reconcile(interval_seconds=1,max_cycles=1)
            self.assertEqual(
                r["status"],
                "BLOCKED_EXIT_BROKER_ORDER_ID_MISMATCH",
            )

    def test_nonfilled_terminal_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            write_sources(td)
            fake=FakeClient(
                status="canceled",
                filled_qty="0",
                filled_avg_price=None,
            )
            c=FinalExitFillReconciliationRoundTripLedgerV2127(
                td,
                client_factory=lambda:fake,
                sleep_fn=lambda _:None,
                now_fn=self.fixed_now,
            )
            r=c.reconcile(interval_seconds=1,max_cycles=1)
            self.assertEqual(r["status"],"BLOCKED_EXIT_NOT_FILLED")

    def test_status_contract(self):
        s=build_v2_1_27_status()
        self.assertTrue(s["v2_1_23_entry_fill_reused"])
        self.assertTrue(s["v2_1_25_exit_submission_reused"])
        self.assertTrue(s["alpaca_paper_read_client_reused"])
        self.assertTrue(s["completed_round_trip_dedup"])
        self.assertTrue(s["fill_based_gross_pnl"])
        self.assertFalse(s["fees_claimed_in_pnl"])
        self.assertFalse(s["new_broker_write_created"])
        self.assertEqual(s["install_test_paper_orders"],0)
        self.assertFalse(s["live_trading_enabled"])


if __name__=="__main__":
    unittest.main()
