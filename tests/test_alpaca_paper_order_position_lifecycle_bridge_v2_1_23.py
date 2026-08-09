from pathlib import Path
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from broker_integration_v1.alpaca_paper_order_position_lifecycle_bridge_v2_1_23 import (
    AlpacaPaperOrderPositionLifecycleBridgeV2123,
)
from broker_integration_v1.alpaca_paper_order_position_lifecycle_status_v2_1_23 import (
    build_v2_1_23_status,
)

def write_submission(root):
    p=Path(root)/"runtime"/"alpaca_paper_bounded_execution_v2_1_22"
    p.mkdir(parents=True,exist_ok=True)
    row={
        "status":"PAPER_ORDER_SUBMITTED_BOUNDED",
        "evidence_key":"ev1",
        "client_order_id":"paper-v2122-fixture",
        "paper_order_submitted":True,
        "live_order_submitted":False,
        "selected_candidate":{"symbol":"AAPL","side":"buy"},
        "order":{
            "id":"broker-1",
            "client_order_id":"paper-v2122-fixture",
            "symbol":"AAPL","side":"buy","status":"accepted",
        },
    }
    (p/"execution_ledger.jsonl").write_text(json.dumps(row)+"\n",encoding="utf-8")

def write_policy(root):
    p=Path(root)/"release"/"v95_33_to_v95_64"/"input"
    p.mkdir(parents=True,exist_ok=True)
    (p/"position_lifecycle_policy.json").write_text(json.dumps({
        "stop_loss_pct":5.0,"take_profit_pct":10.0,
        "trailing_stop_pct":4.0,"maximum_holding_days":20,
    }),encoding="utf-8")

class FakeMonitor:
    def monitor(self,**kwargs):
        return {
            "status":"PASS",
            "final_status":"filled",
            "actual_broker_read_performed":True,
            "actual_broker_write_performed":False,
            "actual_order_submission_performed":False,
            "final_snapshot":{
                "position_found":True,
                "position":{
                    "avg_entry_price":"100",
                    "qty":"0.25",
                    "current_price":"101",
                },
            },
        }

class T(unittest.TestCase):
    def test_waits_without_submission(self):
        with tempfile.TemporaryDirectory() as td:
            r=AlpacaPaperOrderPositionLifecycleBridgeV2123(td).build_dry_plan()
            self.assertEqual(r["status"],"WAITING_FOR_V2_1_22_PAPER_ORDER")

    def test_dry_plan_no_network(self):
        with tempfile.TemporaryDirectory() as td:
            write_submission(td)
            r=AlpacaPaperOrderPositionLifecycleBridgeV2123(td).build_dry_plan()
            self.assertEqual(r["status"],"READY_FOR_READ_ONLY_ORDER_LIFECYCLE_MONITOR")
            self.assertFalse(r["broker_write_allowed"])
            self.assertFalse(r["exit_order_submitted"])

    def test_fake_monitor_reuses_exit_rules(self):
        with tempfile.TemporaryDirectory() as td:
            write_submission(td); write_policy(td)
            b=AlpacaPaperOrderPositionLifecycleBridgeV2123(
                td,monitor_factory=lambda:FakeMonitor()
            )
            r=b.monitor_once()
            self.assertEqual(r["status"],"PASS_ORDER_POSITION_LIFECYCLE_READ_ONLY")
            self.assertEqual(r["position_lifecycle_state"],"POSITION_HOLD_READ_ONLY")
            self.assertEqual(r["position_exit_decision"]["action"],"HOLD")
            self.assertFalse(r["broker_write_performed"])
            self.assertFalse(r["exit_order_submitted"])

    def test_status_contract(self):
        s=build_v2_1_23_status()
        self.assertTrue(s["existing_paper_order_lifecycle_monitor_reused"])
        self.assertTrue(s["existing_position_exit_rules_reused"])
        self.assertFalse(s["new_exit_strategy_created"])
        self.assertFalse(s["broker_write_allowed_from_stage"])
        self.assertEqual(s["install_test_paper_orders"],0)
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__": unittest.main()
