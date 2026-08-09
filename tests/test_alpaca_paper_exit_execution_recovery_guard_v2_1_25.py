from pathlib import Path
from datetime import datetime,timezone
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.alpaca_paper_exit_execution_recovery_guard_v2_1_25 import (
    AlpacaPaperExitExecutionRecoveryGuardV2125,
    EXIT_CONFIRMATION,
)
from broker_integration_v1.alpaca_paper_exit_execution_recovery_status_v2_1_25 import (
    build_v2_1_25_status,
)


def write_lifecycle(root, *, exit_ready=True, symbol="AAPL"):
    p=Path(root)/"runtime"/"alpaca_paper_order_position_lifecycle_v2_1_23"
    p.mkdir(parents=True,exist_ok=True)

    row={
        "status":"PASS_ORDER_POSITION_LIFECYCLE_READ_ONLY",
        "evidence_key":"fixture-evidence-001",
        "client_order_id":"paper-v2122-fixture",
        "selected_candidate":{
            "symbol":symbol,
            "side":"buy",
        },
        "position_lifecycle_state":(
            "POSITION_EXIT_READY_READ_ONLY"
            if exit_ready
            else "POSITION_HOLD_READ_ONLY"
        ),
        "position_exit_decision":{
            "action":"EXIT" if exit_ready else "HOLD",
            "reason":"TAKE_PROFIT" if exit_ready else "NO_EXIT_TRIGGER",
        },
        "order_lifecycle_summary":{
            "final_snapshot":{
                "position_found":True,
                "position":{
                    "symbol":symbol,
                    "qty":"0.25",
                    "avg_entry_price":"100",
                    "current_price":"111",
                },
            },
        },
        "exit_order_submitted":False,
        "live_order_submitted":False,
    }

    (p/"latest_lifecycle.json").write_text(
        json.dumps(row),
        encoding="utf-8",
    )


class FakeOrder:
    id="exit-order-1"
    client_order_id="exit-client-1"
    symbol="AAPL"
    side="sell"
    status="accepted"


class FakeClient:
    def __init__(self):
        self.close_calls=[]

    def close_position(self,symbol):
        self.close_calls.append(symbol)
        return FakeOrder()


class FakeAdapter:
    def __init__(self,open_symbols=None):
        # IMPORTANT:
        # None means "use the normal fixture default AAPL".
        # An explicitly supplied empty set must stay empty so restart recovery
        # can correctly simulate an already-closed Paper position.
        self._open=(
            {"AAPL"}
            if open_symbols is None
            else set(open_symbols)
        )
        self.client=FakeClient()

    def open_position_symbols(self):
        return set(self._open)

    def _client(self):
        return self.client


class FakeService:
    def __init__(self,open_symbols=None,preflight="PASS"):
        self.adapter=FakeAdapter(open_symbols)
        self.preflight_status=preflight

    def preflight(self):
        return {
            "status":self.preflight_status,
            "paper":True,
            "market_open":True,
            "arm_token_valid":True,
            "live_submission_enabled":False,
        }


class T(unittest.TestCase):
    def fixed_now(self):
        return datetime(2026,8,10,15,0,tzinfo=timezone.utc)

    def test_waits_without_lifecycle(self):
        with tempfile.TemporaryDirectory() as td:
            r=AlpacaPaperExitExecutionRecoveryGuardV2125(td).build_plan()
            self.assertEqual(r["status"],"WAITING_FOR_V2_1_23_LIFECYCLE")

    def test_hold_does_not_exit(self):
        with tempfile.TemporaryDirectory() as td:
            write_lifecycle(td,exit_ready=False)
            r=AlpacaPaperExitExecutionRecoveryGuardV2125(td).build_plan()
            self.assertEqual(r["status"],"NO_ACTION_POSITION_NOT_EXIT_READY")
            self.assertFalse(r["paper_exit_order_submitted"])

    def test_exit_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as td:
            write_lifecycle(td)
            svc=FakeService()
            b=AlpacaPaperExitExecutionRecoveryGuardV2125(
                td,
                service_factory=lambda:svc,
                now_fn=self.fixed_now,
            )
            r=b.execute_once("WRONG")
            self.assertEqual(
                r["status"],
                "BLOCKED_EXPLICIT_EXIT_CONFIRMATION_REQUIRED",
            )
            self.assertEqual(svc.adapter.client.close_calls,[])

    def test_fake_paper_exit_exactly_once(self):
        with tempfile.TemporaryDirectory() as td:
            write_lifecycle(td)
            svc=FakeService()
            b=AlpacaPaperExitExecutionRecoveryGuardV2125(
                td,
                service_factory=lambda:svc,
                now_fn=self.fixed_now,
            )

            first=b.execute_once(EXIT_CONFIRMATION)
            self.assertEqual(
                first["status"],
                "PAPER_EXIT_ORDER_SUBMITTED_ONCE",
            )
            self.assertTrue(first["paper_exit_order_submitted"])
            self.assertFalse(first["live_order_submitted"])
            self.assertEqual(svc.adapter.client.close_calls,["AAPL"])

            second=b.execute_once(EXIT_CONFIRMATION)
            self.assertEqual(
                second["status"],
                "BLOCKED_EXIT_ALREADY_SUBMITTED",
            )
            self.assertEqual(svc.adapter.client.close_calls,["AAPL"])

    def test_restart_already_closed_no_duplicate(self):
        with tempfile.TemporaryDirectory() as td:
            write_lifecycle(td)

            # Explicit empty set must remain empty.
            svc=FakeService(open_symbols=set())
            self.assertEqual(
                svc.adapter.open_position_symbols(),
                set(),
            )

            b=AlpacaPaperExitExecutionRecoveryGuardV2125(
                td,
                service_factory=lambda:svc,
                now_fn=self.fixed_now,
            )
            r=b.execute_once(EXIT_CONFIRMATION)

            self.assertEqual(
                r["status"],
                "RECOVERED_POSITION_ALREADY_CLOSED_NO_DUPLICATE_EXIT",
            )
            self.assertTrue(r["recovery_guard_triggered"])
            self.assertFalse(r["paper_exit_order_submitted"])
            self.assertEqual(svc.adapter.client.close_calls,[])

    def test_preflight_blocks_exit(self):
        with tempfile.TemporaryDirectory() as td:
            write_lifecycle(td)
            svc=FakeService(preflight="BLOCKED")
            b=AlpacaPaperExitExecutionRecoveryGuardV2125(
                td,
                service_factory=lambda:svc,
                now_fn=self.fixed_now,
            )
            r=b.execute_once(EXIT_CONFIRMATION)
            self.assertEqual(r["status"],"BLOCKED_PAPER_PREFLIGHT")
            self.assertEqual(svc.adapter.client.close_calls,[])

    def test_local_recovery_no_network(self):
        with tempfile.TemporaryDirectory() as td:
            b=AlpacaPaperExitExecutionRecoveryGuardV2125(td)
            r=b.recover_state()
            self.assertEqual(
                r["status"],
                "PASS_LOCAL_RESTART_RECOVERY_STATE",
            )
            self.assertFalse(r["broker_network_used"])

    def test_status_contract(self):
        s=build_v2_1_25_status()
        self.assertTrue(s["v2_1_23_exit_ready_required"])
        self.assertTrue(s["existing_paper_true_client_reused"])
        self.assertTrue(s["alpaca_official_close_position_used"])
        self.assertFalse(s["new_live_client_created"])
        self.assertTrue(s["one_time_exit_fingerprint_guard"])
        self.assertEqual(s["install_test_paper_exit_orders"],0)
        self.assertFalse(s["live_trading_enabled"])


if __name__=="__main__":
    unittest.main()
