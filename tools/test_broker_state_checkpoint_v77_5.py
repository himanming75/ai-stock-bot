from __future__ import annotations

import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from broker.broker_state_checkpoint_v77_5 import (
    BrokerStateCheckpointManager,
    CheckpointError,
)
from broker.contracts_v77_1 import (
    BrokerOrderRequest,
    OrderSide,
    OrderType,
    TimeInForce,
)
from broker.order_lifecycle_simulator_v77_3 import OrderLifecycleSimulator
from tools.broker_state_checkpoint_v77_5 import verify, write_outputs
from tools.verify_broker_state_checkpoint_v77_5 import verify_output


class CheckpointTests(unittest.TestCase):
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

    def test_create_and_verify(self):
        checkpoint = BrokerStateCheckpointManager().create(
            self.scenario(), checkpoint_id="CP-1"
        )
        self.assertTrue(BrokerStateCheckpointManager().verify(checkpoint))
        self.assertEqual(len(checkpoint.orders), 1)
        self.assertEqual(len(checkpoint.fills), 1)

    def test_round_trip(self):
        manager = BrokerStateCheckpointManager()
        checkpoint = manager.create(self.scenario(), checkpoint_id="CP-2")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"checkpoint.json"
            manager.write(checkpoint, path)
            loaded = manager.read(path)
        self.assertEqual(loaded.as_dict(), checkpoint.as_dict())

    def test_tamper_detected(self):
        manager = BrokerStateCheckpointManager()
        checkpoint = manager.create(self.scenario(), checkpoint_id="CP-3")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"checkpoint.json"
            manager.write(checkpoint, path)
            value = json.loads(path.read_text(encoding="utf-8"))
            value["cash"] = "1"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(CheckpointError):
                manager.read(path)

    def test_unreconciled_state_rejected(self):
        sim = self.scenario()
        sim._cash += Decimal("1")
        with self.assertRaises(CheckpointError):
            BrokerStateCheckpointManager().create(sim, checkpoint_id="CP-4")

    def test_verification_outputs(self):
        config = {
            "expected_framework_commit_sha": "a"*7,
            "expected_v77_4_reconciliation_sha256": "b"*64,
            "expected_v77_4_verification_sha256": "c"*64,
            "required_schema_version": "v77.5.broker_state_checkpoint.1",
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root/"release/v77_4/output"
            out.mkdir(parents=True)
            (out/"execution_event_reconciliation_verification_v77_4.json").write_text(
                json.dumps({
                    "status": "PASS",
                    "execution_event_reconciliation_sha256": "b"*64,
                    "verification_sha256": "c"*64,
                    "next_phase": "V77_5_BROKER_STATE_CHECKPOINT",
                }),
                encoding="utf-8",
            )
            git = {
                "head_sha": "d"*40,
                "origin_main_sha": "d"*40,
                "branch": "main",
            }
            with (
                patch("tools.broker_state_checkpoint_v77_5.git_state",
                      return_value=git),
                patch("tools.broker_state_checkpoint_v77_5.git_is_ancestor",
                      return_value=True),
            ):
                result = verify(root, config)
            self.assertEqual(result["status"], "PASS")
            output_dir = root/"release/v77_5/output"
            write_outputs(result, output_dir)
            self.assertTrue(verify_output(output_dir)["verified"])


if __name__ == "__main__":
    unittest.main()
