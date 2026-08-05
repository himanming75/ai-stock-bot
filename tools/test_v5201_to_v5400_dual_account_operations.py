from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from dual_account_operations.dashboard import (
    build_dashboard,
)
from dual_account_operations.fixtures import (
    ACCOUNTS,
)
from dual_account_operations.profiles import (
    PolicyProfileCatalog,
)
from dual_account_operations.service import (
    DualAccountOperationsCertificationService,
)
from dual_account_operations.transition import (
    validate_transition,
)


class Tests(unittest.TestCase):
    def test_profile_catalog(self):
        catalog = PolicyProfileCatalog()
        self.assertEqual(
            len(catalog.all()),
            5,
        )

    def test_paper_dashboard(self):
        profile = PolicyProfileCatalog().get(
            "PAPER_TEST"
        )
        dashboard = build_dashboard(
            active_profile=profile.name,
            accounts=ACCOUNTS,
            policy_profile=profile.to_dict(),
            global_kill_switch=False,
        )
        self.assertEqual(
            dashboard[
                "effective_read_account_count"
            ],
            1,
        )
        self.assertEqual(
            dashboard[
                "effective_write_account_count"
            ],
            0,
        )

    def test_etrade_requires_ack(self):
        result = validate_transition(
            "ALL_STOP",
            "ETRADE_READ_ONLY",
            operator_ack=False,
            etrade_actual_connection_validated=True,
        )
        self.assertFalse(result["allowed"])

    def test_etrade_requires_validation(self):
        result = validate_transition(
            "ALL_STOP",
            "ETRADE_READ_ONLY",
            operator_ack=True,
            etrade_actual_connection_validated=False,
        )
        self.assertFalse(result["allowed"])
        self.assertEqual(
            result["reason"],
            "ETRADE_ACTUAL_CONNECTION_NOT_VALIDATED",
        )

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                DualAccountOperationsCertificationService()
                .evaluate(
                    output_dir=Path(directory)
                )
            )
            self.assertEqual(
                result["status"],
                "PASS",
            )
            self.assertTrue(
                result[
                    "future_multi_account_dashboard_ready"
                ]
            )

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            DualAccountOperationsCertificationService().evaluate(
                output_dir=root
            )
            self.assertTrue(
                (
                    root
                    / "dual_account_operations_dashboard.csv"
                ).exists()
            )
            self.assertTrue(
                (
                    root
                    / "dual_account_operations_ledger.jsonl"
                ).exists()
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                DualAccountOperationsCertificationService()
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
