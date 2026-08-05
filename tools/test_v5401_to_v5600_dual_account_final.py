from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from dual_account_controller.controller import (
    DualAccountOperationsController,
)
from dual_account_controller.service import (
    DualAccountFinalCertificationService,
)


class Tests(unittest.TestCase):
    def controller(self, root: Path):
        return DualAccountOperationsController(
            state_path=root / "state.json",
            ledger_path=root / "ledger.jsonl",
            etrade_actual_connection_validated=False,
        )

    def test_default_restore_is_all_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            state = self.controller(
                Path(directory)
            ).restore()
            self.assertEqual(
                state.active_profile,
                "ALL_STOP",
            )
            self.assertTrue(
                state.global_kill_switch
            )

    def test_profile_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = self.controller(
                Path(directory)
            )
            controller.transition(
                "PAPER_TEST",
                operator_ack=False,
                reason="TEST",
            )
            controller.lock_profile()
            result = controller.transition(
                "DUAL_MONITOR",
                operator_ack=True,
                reason="TEST",
            )
            self.assertFalse(result.allowed)
            self.assertEqual(
                result.reason,
                "PROFILE_LOCK_ACTIVE",
            )

    def test_etrade_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = self.controller(
                Path(directory)
            )
            result = controller.transition(
                "ETRADE_READ_ONLY",
                operator_ack=True,
                reason="TEST",
            )
            self.assertFalse(result.allowed)

    def test_emergency_all_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = self.controller(
                Path(directory)
            )
            controller.transition(
                "PAPER_TEST",
                operator_ack=False,
                reason="TEST",
            )
            state = controller.emergency_guard(
                critical_condition=True,
                reason="CRITICAL",
            )
            self.assertEqual(
                state.active_profile,
                "ALL_STOP",
            )
            self.assertTrue(
                state.global_kill_switch
            )

    def test_restart_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = self.controller(root)
            controller.transition(
                "PAPER_TEST",
                operator_ack=False,
                reason="TEST",
            )
            controller.activate_global_kill_switch(
                reason="STOP",
            )
            restored = self.controller(
                root
            ).restore()
            self.assertEqual(
                restored.active_profile,
                "ALL_STOP",
            )
            self.assertTrue(
                restored.global_kill_switch
            )

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                DualAccountFinalCertificationService()
                .evaluate(
                    output_dir=Path(directory)
                )
            )
            self.assertEqual(
                result["status"],
                "PASS",
            )
            self.assertEqual(
                result[
                    "fourth_stage_final_certification"
                ],
                "PASS",
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                DualAccountFinalCertificationService()
                .evaluate(
                    output_dir=Path(directory)
                )
            )
            self.assertFalse(
                result[
                    "actual_broker_write_performed"
                ]
            )
            self.assertEqual(
                result[
                    "actual_paper_orders_submitted"
                ],
                0,
            )
            self.assertEqual(
                result[
                    "actual_live_orders_submitted"
                ],
                0,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
