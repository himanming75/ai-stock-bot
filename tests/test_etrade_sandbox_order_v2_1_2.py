from pathlib import Path
from decimal import Decimal
import json
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker.contracts_v77_1 import (
    BrokerOrderRequest,
    OrderSide,
    OrderType,
    TimeInForce,
)
from broker_integration_v1.etrade_sandbox_order_ledger_v2_1_2 import (
    SandboxOrderLedger,
)
from broker_integration_v1.etrade_sandbox_order_reconciliation_v2_1_2 import (
    reconcile_sandbox_place,
)
from broker_integration_v1.etrade_sandbox_orders_reader_v2_1_2 import (
    ETradeSandboxOrdersReader,
)
from broker_integration_v1.etrade_sandbox_order_status_v2_1_2 import (
    build_etrade_sandbox_order_v2_1_2_status,
)


class FakeReadTransport:
    def __init__(self,payload):
        self.payload=payload
        self.calls=[]
    def get_json(self,path):
        self.calls.append(path)
        return self.payload


class TestV212(unittest.TestCase):
    def test_reconciliation_matched(self):
        result=reconcile_sandbox_place(
            {"order_id":"123"},
            {"OrdersResponse":{"Order":[{"orderId":123}]}}
        )
        self.assertEqual(result["status"],"MATCHED")
        self.assertEqual(result["matched_order_count"],1)

    def test_reconciliation_sample_data_mismatch(self):
        result=reconcile_sandbox_place(
            {"order_id":"123"},
            {"OrdersResponse":{"Order":[{"orderId":999}]}}
        )
        self.assertEqual(result["status"],"SAMPLE_DATA_MISMATCH")

    def test_reconciliation_not_observed(self):
        result=reconcile_sandbox_place(
            {"order_id":"123"},
            {"OrdersResponse":{"Order":[]}}
        )
        self.assertEqual(result["status"],"NOT_OBSERVED")

    def test_orders_reader_reuses_read_transport(self):
        t=FakeReadTransport({"OrdersResponse":{"Order":[]}})
        r=ETradeSandboxOrdersReader(t).list_orders_safe("ABC")
        self.assertEqual(r["status"],"PASS")
        self.assertEqual(t.calls,["/accounts/ABC/orders.json"])

    def test_ledger_does_not_store_raw_account_key(self):
        with tempfile.TemporaryDirectory() as td:
            ledger=SandboxOrderLedger(td)
            request=BrokerOrderRequest(
                client_order_id="x",
                symbol="AAPL",
                side=OrderSide.BUY,
                quantity=Decimal("1"),
                order_type=OrderType.MARKET,
                time_in_force=TimeInForce.DAY,
                strategy_id="TEST",
            )
            ledger.record_preview(
                "RAW_ACCOUNT_SECRET_KEY",
                request,
                {
                    "client_order_id":"ABC",
                    "preview_id":1,
                    "status":"PASS_SANDBOX_PREVIEW",
                },
            )
            text=ledger.path.read_text(encoding="utf-8")
            self.assertNotIn("RAW_ACCOUNT_SECRET_KEY",text)
            self.assertIn("account_fingerprint",text)

    def test_status_safety(self):
        s=build_etrade_sandbox_order_v2_1_2_status()
        self.assertTrue(s["explicit_place_confirmation_required"])
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])
        self.assertFalse(s["profitability_validation"])
        self.assertFalse(s["contracts"]["duplicate_order_engine_created"])


if __name__=="__main__":
    unittest.main()
