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
from broker.restart_recovery_replay_v77_6 import RestartRecoveryReplay
from tools.restart_recovery_replay_v77_6 import verify, write_outputs
from tools.verify_restart_recovery_replay_v77_6 import verify_output


class RecoveryTests(unittest.TestCase):
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
        sim.apply_fill(buy.broker_order_id, quantity=Decimal("4"), price=Decimal("100"))
        sim.apply_fill(buy.broker_order_id, quantity=Decimal("6"), price=Decimal("110"))
        return sim

    def test_restore_and_replay(self):
        manager = BrokerStateCheckpointManager()
        checkpoint = manager.create(self.scenario(), checkpoint_id="REC-1")
        recovery = RestartRecoveryReplay(checkpoint_manager=manager)
        restored = recovery.restore(checkpoint)
        report = recovery.verify_replay(checkpoint, restored)
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["checks"]["state_sha256_match"])

    def test_sequences_restored(self):
        manager = BrokerStateCheckpointManager()
        checkpoint = manager.create(self.scenario(), checkpoint_id="REC-2")
        restored = RestartRecoveryReplay(
            checkpoint_manager=manager
        ).restore(checkpoint)
        self.assertEqual(restored._order_sequence, 1)
        self.assertEqual(restored._fill_sequence, 2)
        self.assertEqual(restored._event_sequence, 4)

    def test_recovered_state_can_continue(self):
        manager = BrokerStateCheckpointManager()
        checkpoint = manager.create(self.scenario(), checkpoint_id="REC-3")
        restored = RestartRecoveryReplay(
            checkpoint_manager=manager
        ).restore(checkpoint)
        sell = restored.submit_order(BrokerOrderRequest(
            client_order_id="sell-1",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=Decimal("1"),
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
        ))
        restored.apply_fill(
            sell.broker_order_id,
            quantity=Decimal("1"),
            price=Decimal("120"),
        )
        self.assertEqual(restored.get_account_snapshot().positions[0].quantity,
                         Decimal("9"))

    def test_verification_outputs(self):
        config = {
            "expected_framework_commit_sha": "a"*7,
            "expected_v77_5_checkpoint_sha256": "b"*64,
            "expected_v77_5_sample_state_sha256": "c"*64,
            "expected_v77_5_verification_sha256": "d"*64,
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root/"release/v77_5/output"
            out.mkdir(parents=True)

            manager = BrokerStateCheckpointManager()
            checkpoint = manager.create(self.scenario(), checkpoint_id="V77-5-PRIMARY")
            manager.write(
                checkpoint,
                out/"sample_broker_state_checkpoint_v77_5.json",
            )
            (out/"broker_state_checkpoint_verification_v77_5.json").write_text(
                json.dumps({
                    "status": "PASS",
                    "broker_state_checkpoint_sha256": "b"*64,
                    "sample_checkpoint": {"state_sha256": "c"*64},
                    "verification_sha256": "d"*64,
                    "next_phase": "V77_6_RESTART_RECOVERY_REPLAY",
                }),
                encoding="utf-8",
            )
            git = {
                "head_sha": "e"*40,
                "origin_main_sha": "e"*40,
                "branch": "main",
            }
            with (
                patch("tools.restart_recovery_replay_v77_6.git_state",
                      return_value=git),
                patch("tools.restart_recovery_replay_v77_6.git_is_ancestor",
                      return_value=True),
            ):
                result = verify(root, config)
            self.assertEqual(result["status"], "PASS")
            output_dir = root/"release/v77_6/output"
            write_outputs(result, output_dir)
            self.assertTrue(verify_output(output_dir)["verified"])


if __name__ == "__main__":
    unittest.main()
