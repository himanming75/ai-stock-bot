from __future__ import annotations

import unittest

from etrade_live_audit.canonicalizer import canonicalize_etrade_live


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
                rec("multi_broker_etrade/auth.py", ["oauth_token"]),
                rec("multi_broker_etrade/client.py", [
                    "api_etrade_com", "list_accounts", "positions",
                    "quote", "preview_order", "place_order",
                    "list_orders", "cancel_order"
                ]),
                rec("deployment/credential_vault.py", [
                    "consumer_key", "consumer_secret", "production"
                ]),
                rec("broker_safe_execution/gateway.py", [
                    "duplicate_order", "daily_loss_limit", "kill_switch"
                ]),
                rec("broker_integration/actual_validation.py", [
                    "reconcile_orders", "reconcile_positions"
                ]),
            ]
        }

    def test_complete_pipeline(self):
        result = canonicalize_etrade_live(self._audit())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["missing_capabilities"], [])

    def test_scope_and_roles_locked(self):
        result = canonicalize_etrade_live(self._audit())
        self.assertEqual(result["broker_scope"]["paper_broker"], "ALPACA")
        self.assertEqual(result["broker_scope"]["live_broker"], "ETRADE")
        self.assertFalse(result["broker_scope"]["other_brokers_enabled"])

    def test_live_write_off(self):
        result = canonicalize_etrade_live(self._audit())
        self.assertFalse(result["etrade_live_submission_enabled"])
        self.assertFalse(result["etrade_live_cancel_enabled"])
        self.assertFalse(result["etrade_live_allocation_enabled"])
        self.assertEqual(result["actual_live_orders_submitted"], 0)

    def test_tests_and_sandbox_excluded(self):
        audit = self._audit()
        audit["records"].append(
            rec("tools/test_etrade.py", ["place_order"], score=99999)
        )
        audit["records"].append(
            rec("etrade_sandbox/client.py", ["place_order"], score=99999)
        )
        result = canonicalize_etrade_live(audit)
        chosen = result["selected"]["order_place"]["selected"]["path"]
        self.assertNotIn("test_", chosen)
        self.assertNotIn("sandbox", chosen)

    def test_missing_capability_review(self):
        audit = self._audit()
        audit["records"] = [
            item for item in audit["records"]
            if (
                "actual_validation" not in item["path"]
                and "recovery" not in item["path"]
                and "reconcile" not in " ".join(item.get("functions", [])).lower()
            )
        ]
        result = canonicalize_etrade_live(audit)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertIn(
            "restart_reconciliation",
            result["missing_capabilities"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
