from __future__ import annotations

import unittest

from single_account_audit.canonicalizer import canonicalize_single_account


def rec(path, functions=(), classes=(), score=0):
    return {
        "path": path,
        "functions": list(functions),
        "classes": list(classes),
        "score": score,
        "modified_ns": 1,
        "categories": [],
        "safety_flags": {},
    }


class Tests(unittest.TestCase):
    def _audit(self):
        return {
            "records": [
                rec("deployment/credential_vault.py", [
                    "alpaca_paper_account",
                    "etrade_live_account",
                    "account_id_allowlist",
                    "credential_account_match",
                ]),
                rec("broker_safe_execution/gateway.py", [
                    "broker_account_role_lock",
                    "pre_order_account_validation",
                    "wrong_account_hard_block",
                    "account_switch_prohibition",
                ]),
                rec("broker_integration/actual_validation.py", [
                    "restart_account_revalidation",
                    "account_reconciliation",
                ]),
                rec("paper_automation_controller/checkpoint.py", [
                    "checkpoint_account_identity",
                ]),
                rec("system_health_monitoring/service.py", [
                    "dashboard_account_broker_mode",
                ]),
                rec("paper_automation_controller/controller.py", [
                    "single_account_runtime_lock",
                ]),
            ]
        }

    def test_complete_pipeline(self):
        result = canonicalize_single_account(self._audit())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["missing_capabilities"], [])

    def test_roles_and_scope_locked(self):
        result = canonicalize_single_account(self._audit())
        self.assertTrue(result["scope_locked"])
        self.assertFalse(result["multi_account_enabled"])
        self.assertEqual(
            result["account_roles"]["alpaca"]["mode"],
            "PAPER_ONLY",
        )
        self.assertEqual(
            result["account_roles"]["etrade"]["mode"],
            "LIVE_ONLY",
        )

    def test_account_switch_off(self):
        result = canonicalize_single_account(self._audit())
        self.assertFalse(result["runtime_account_switch_enabled"])
        self.assertFalse(result["automatic_account_discovery_enabled"])

    def test_zero_order_contract(self):
        result = canonicalize_single_account(self._audit())
        self.assertFalse(result["live_submission_enabled"])
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)

    def test_test_and_release_excluded(self):
        audit = self._audit()
        audit["records"].append(
            rec("tools/test_account_binding.py", [
                "single_account_runtime_lock"
            ], score=99999)
        )
        audit["records"].append(
            rec("release/v1/account_binding.py", [
                "single_account_runtime_lock"
            ], score=99999)
        )
        result = canonicalize_single_account(audit)
        selected = result["selected"][
            "single_account_runtime_lock"
        ]["selected"]["path"]
        self.assertNotIn("test_", selected)
        self.assertNotIn("release/", selected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
