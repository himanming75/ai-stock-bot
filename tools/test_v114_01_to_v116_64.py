import tempfile,unittest
from pathlib import Path

from broker_safe_execution.intents import build_order_intents
from broker_safe_execution.validation import validate_all
from broker_safe_execution.approval import build_manual_approval_package
from broker_safe_execution.translators import translate_intent
from broker_safe_execution.queue import build_queue
from broker_safe_execution.gateway import evaluate_gateway
from broker_safe_execution.sync import (
    simulate_fill_sync,simulate_position_sync,simulate_cancel_replace
)
from broker_safe_execution.engine import evaluate

POLICY={
    "allowed_symbols":["AAPL"],
    "maximum_order_quantity":100,
    "maximum_order_notional":25000,
    "sample_order_intents":[{
        "symbol":"AAPL",
        "side":"BUY",
        "quantity":10,
        "order_type":"LIMIT",
        "limit_price":200,
    }],
    "external_network_enabled":False,
    "broker_submission_enabled":False,
}

class Tests(unittest.TestCase):
    def test_intents(self):
        rows=build_order_intents(100000,POLICY)
        self.assertEqual(rows[0]["estimated_notional"],2000)

    def test_validation(self):
        intents=build_order_intents(100000,POLICY)
        self.assertTrue(validate_all(intents,POLICY)["passed"])

    def test_approval(self):
        intents=build_order_intents(100000,POLICY)
        validation=validate_all(intents,POLICY)
        approval=build_manual_approval_package(intents,validation)
        self.assertFalse(approval["approval_granted"])

    def test_translation(self):
        intent=build_order_intents(100000,POLICY)[0]
        value=translate_intent(intent,"ALPACA_READ_ONLY")
        self.assertFalse(value["submitted"])

    def test_queue(self):
        intents=build_order_intents(100000,POLICY)
        validation=validate_all(intents,POLICY)
        translated=[translate_intent(intents[0],"MOCK_READ_ONLY")]
        value=build_queue(intents,validation,translated)
        self.assertEqual(value["ready_for_approval_count"],1)

    def test_gateway(self):
        intents=build_order_intents(100000,POLICY)
        validation=validate_all(intents,POLICY)
        approval=build_manual_approval_package(intents,validation)
        self.assertTrue(evaluate_gateway(approval,POLICY)["passed"])

    def test_sync(self):
        queue={"rows":[{"intent_id":"i","symbol":"AAPL"}]}
        self.assertFalse(simulate_fill_sync(queue)[
            "real_broker_sync_performed"
        ])
        self.assertEqual(simulate_position_sync()[
            "position_sync_count"
        ],0)
        self.assertEqual(simulate_cancel_replace(queue)[
            "cancel_requests_executed"
        ],0)

    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as temp:
            result=evaluate(Path(temp))
            self.assertEqual(
                result["state"],
                "BROKER_SAFE_EXECUTION_SOURCE_REQUIRED",
            )

    def test_orders_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(
                evaluate(Path(temp))["actual_orders_submitted"],0
            )

if __name__=="__main__":
    unittest.main()
