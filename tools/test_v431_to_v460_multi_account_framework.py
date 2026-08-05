from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from pathlib import Path

from multi_account_framework.io import write_json
from multi_account_framework.service import (
    MultiAccountFrameworkService,
)


class Tests(unittest.TestCase):
    def create_inputs(self, root: Path, duplicate=False):
        accounts = [
            {
                "alias": "paper_primary",
                "display_name": "Primary Paper",
                "broker": "alpaca",
                "mode": "paper",
                "enabled": False,
                "broker_network_enabled": False,
                "order_submission_enabled": False,
                "credential_aliases": {
                    "key_id_env": "APCA_PAPER_1_KEY_ID",
                    "secret_key_env": "APCA_PAPER_1_SECRET_KEY",
                    "base_url_env": "APCA_PAPER_1_BASE_URL",
                },
                "risk_policy": {
                    "max_daily_loss_percent": "2",
                },
                "controller_profile": {
                    "profile": "READ_ONLY",
                },
            }
        ]
        if duplicate:
            accounts.append(dict(accounts[0]))

        registry = root / "registry.json"
        write_json(registry, {"accounts": accounts})
        policy = root / "policy.json"
        write_json(
            policy,
            {
                "policy_version": 1,
                "maximum_accounts": 10,
                "global_broker_network_enabled": False,
                "global_order_submission_enabled": False,
            },
        )
        return registry, policy

    def test_valid_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry, policy = self.create_inputs(root)
            result = MultiAccountFrameworkService().evaluate(
                registry_path=registry,
                policy_path=policy,
                output_dir=root / "out",
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["valid_account_count"], 1)

    def test_duplicate_alias_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry, policy = self.create_inputs(
                root, duplicate=True
            )
            result = MultiAccountFrameworkService().evaluate(
                registry_path=registry,
                policy_path=policy,
                output_dir=root / "out",
            )
            self.assertIn(
                "paper_primary",
                result["duplicate_aliases"],
            )

    def test_credentials_are_aliases_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry, policy = self.create_inputs(root)
            result = MultiAccountFrameworkService().evaluate(
                registry_path=registry,
                policy_path=policy,
                output_dir=root / "out",
            )
            self.assertFalse(
                result["credential_values_stored"]
            )
            self.assertTrue(
                result["credential_aliases_only"]
            )

    def test_per_account_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry, policy = self.create_inputs(root)
            out = root / "out"
            MultiAccountFrameworkService().evaluate(
                registry_path=registry,
                policy_path=policy,
                output_dir=out,
            )
            self.assertTrue(
                (
                    out
                    / "accounts/paper_primary/account_profile.json"
                ).exists()
            )
            self.assertTrue(
                (
                    out
                    / "accounts/paper_primary/account_event_ledger.jsonl"
                ).exists()
            )

    def test_no_network_or_orders(self):
        source = inspect.getsource(
            MultiAccountFrameworkService
        )
        self.assertIn(
            '"actual_external_network_used": False',
            source,
        )
        self.assertIn(
            '"actual_paper_orders_submitted": 0',
            source,
        )
        self.assertIn(
            '"actual_live_orders_submitted": 0',
            source,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
