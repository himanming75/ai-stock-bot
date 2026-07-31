from __future__ import annotations
import json, tempfile, unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from broker.broker_state_checkpoint_v77_5 import BrokerStateCheckpointManager
from broker.contracts_v77_1 import BrokerOrderRequest, OrderSide, OrderType, TimeInForce
from broker.multi_order_continuation_stress_v77_8 import MultiOrderContinuationStress
from broker.order_lifecycle_simulator_v77_3 import OrderLifecycleSimulator
from tools.multi_order_continuation_stress_v77_8 import verify, summary
from tools.verify_multi_order_continuation_stress_v77_8 import verify_output

class StressTests(unittest.TestCase):
    def checkpoint(self):
        sim=OrderLifecycleSimulator()
        order=sim.submit_order(BrokerOrderRequest(
            client_order_id="seed", symbol="AAPL", side=OrderSide.BUY,
            quantity=Decimal("10"), order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY))
        sim.apply_fill(order.broker_order_id, quantity=Decimal("10"), price=Decimal("100"))
        return BrokerStateCheckpointManager().create(sim, checkpoint_id="SEED")

    def test_stress_passes(self):
        sim, report = MultiOrderContinuationStress().run(self.checkpoint())
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.submitted_order_count, 8)
        self.assertEqual(report.applied_fill_count, 12)
        self.assertEqual(sim.actual_orders_submitted, 0)

    def test_positions_expected(self):
        _, report = MultiOrderContinuationStress().run(self.checkpoint())
        positions={x["symbol"]: x["quantity"] for x in report.final_positions}
        self.assertEqual(positions, {"AAPL":"11","MSFT":"7","NVDA":"9"})

    def test_ids_are_unique(self):
        _, report = MultiOrderContinuationStress().run(self.checkpoint())
        self.assertEqual(len(report.new_order_ids), len(set(report.new_order_ids)))
        self.assertEqual(len(report.new_fill_ids), len(set(report.new_fill_ids)))

    def test_verification_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); out5=root/"release/v77_5/output"; out7=root/"release/v77_7/output"
            out5.mkdir(parents=True); out7.mkdir(parents=True)
            cp=self.checkpoint(); BrokerStateCheckpointManager().write(
                cp, out5/"sample_broker_state_checkpoint_v77_5.json")
            (out7/"recovery_continuation_safety_verification_v77_7.json").write_text(
                json.dumps({"status":"PASS",
                    "recovery_continuation_safety_sha256":"b"*64,
                    "continuation_report":{"continued_checkpoint_sha256":"c"*64},
                    "verification_sha256":"d"*64,
                    "next_phase":"V77_8_MULTI_ORDER_CONTINUATION_STRESS"}))
            config={"expected_framework_commit_sha":"a"*7,
                    "expected_v77_7_safety_sha256":"b"*64,
                    "expected_v77_7_continued_checkpoint_sha256":"c"*64,
                    "expected_v77_7_verification_sha256":"d"*64}
            with patch("tools.multi_order_continuation_stress_v77_8.git",
                       side_effect=["e"*40,"e"*40,"main"]), \
                 patch("tools.multi_order_continuation_stress_v77_8.ancestor",
                       return_value=True):
                result=verify(root, config)
            self.assertEqual(result["status"], "PASS")
            out8=root/"release/v77_8/output"; out8.mkdir(parents=True)
            (out8/"multi_order_continuation_stress_verification_v77_8.json").write_text(
                json.dumps(result, indent=2, sort_keys=True))
            (out8/"multi_order_continuation_stress_summary_v77_8.json").write_text(
                json.dumps(summary(result), indent=2, sort_keys=True))
            self.assertTrue(verify_output(out8)["verified"])

if __name__ == "__main__": unittest.main()
