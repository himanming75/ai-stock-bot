from __future__ import annotations

import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from broker.broker_state_checkpoint_v77_5 import BrokerStateCheckpointManager
from broker.contracts_v77_1 import (
    BrokerOrderRequest,
    OrderSide,
    OrderType,
    TimeInForce,
)
from broker.order_lifecycle_simulator_v77_3 import OrderLifecycleSimulator
from broker.recovery_continuation_safety_v77_7 import RecoveryContinuationSafety
from tools.recovery_continuation_safety_v77_7 import verify, write_outputs
from tools.verify_recovery_continuation_safety_v77_7 import verify_output


class ContinuationSafetyTests(unittest.TestCase):
    def scenario(self):
        sim = OrderLifecycleSimulator()
        buy = sim.submit_order(BrokerOrderRequest(
            client_order_id="buy-1",
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("10"),
            order_type=OrderType.LIMIT,
            time_in_force=TimeInForce.DAY,
            limit_price=Decimal("100"),
        ))
        sim.apply_fill(buy.broker_order_id, quantity=Decimal("10"), price=Decimal("100"))
        return sim

    def test_continuation_safety_passes(self):
        manager = BrokerStateCheckpointManager()
        checkpoint = manager.create(self.scenario(), checkpoint_id="CONT-1")
        simulator, report = RecoveryContinuationSafety(
            checkpoint_manager=manager
        ).continue_from_checkpoint(checkpoint)
        self.assertEqual(report.status, "PASS")
        self.assertTrue(report.checks["duplicate_client_order_rejected"])
        self.assertEqual(simulator.actual_orders_submitted, 0)

    def test_identifier_sequences_continue(self):
        manager = BrokerStateCheckpointManager()
        checkpoint = manager.create(self.scenario(), checkpoint_id="CONT-2")
        _, report = RecoveryContinuationSafety(
            checkpoint_manager=manager
        ).continue_from_checkpoint(checkpoint)
        self.assertTrue(report.new_order_id.endswith("-00000002"))
        self.assertTrue(report.new_fill_id.endswith("-00000002"))

    def test_checkpoint_chain_changes(self):
        manager = BrokerStateCheckpointManager()
        checkpoint = manager.create(self.scenario(), checkpoint_id="CONT-3")
        _, report = RecoveryContinuationSafety(
            checkpoint_manager=manager
        ).continue_from_checkpoint(checkpoint)
        self.assertNotEqual(
            report.source_checkpoint_sha256,
            report.continued_checkpoint_sha256,
        )

    def test_verification_outputs(self):
        config = {
            "expected_framework_commit_sha": "a"*7,
            "expected_v77_6_recovery_sha256": "b"*64,
            "expected_v77_6_replayed_state_sha256": "c"*64,
            "expected_v77_6_verification_sha256": "d"*64,
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out5 = root/"release/v77_5/output"
            out6 = root/"release/v77_6/output"
            out5.mkdir(parents=True)
            out6.mkdir(parents=True)

            manager = BrokerStateCheckpointManager()
            checkpoint = manager.create(self.scenario(), checkpoint_id="V77-5-PRIMARY")
            manager.write(
                checkpoint,
                out5/"sample_broker_state_checkpoint_v77_5.json",
            )
            (out6/"restart_recovery_replay_verification_v77_6.json").write_text(
                json.dumps({
                    "status": "PASS",
                    "restart_recovery_replay_sha256": "b"*64,
                    "replay_report": {"replayed_state_sha256": "c"*64},
                    "verification_sha256": "d"*64,
                    "next_phase": "V77_7_RECOVERY_CONTINUATION_SAFETY",
                }),
                encoding="utf-8",
            )
            git = {
                "head_sha": "e"*40,
                "origin_main_sha": "e"*40,
                "branch": "main",
            }
            with (
                patch("tools.recovery_continuation_safety_v77_7.git_state",
                      return_value=git),
                patch("tools.recovery_continuation_safety_v77_7.git_is_ancestor",
                      return_value=True),
            ):
                result = verify(root, config)
            self.assertEqual(result["status"], "PASS")
            output_dir = root/"release/v77_7/output"
            write_outputs(result, output_dir)
            self.assertTrue(verify_output(output_dir)["verified"])


if __name__ == "__main__":
    unittest.main()
