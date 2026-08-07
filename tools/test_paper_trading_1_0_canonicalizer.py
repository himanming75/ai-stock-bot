from __future__ import annotations

import unittest

from paper_completion_audit.canonicalizer import canonicalize


def record(path, categories, *, submit=False, paper=False, live_off=False, score=0):
    return {
        "path": path,
        "categories": categories,
        "score": score,
        "modified_ns": 1,
        "safety_flags": {
            "contains_submit_order": submit,
            "contains_cancel_order": False,
            "contains_delete_all_positions": False,
            "mentions_paper_only": paper,
            "mentions_live_off": live_off,
            "mentions_broker_write_off": False,
        },
    }


class Tests(unittest.TestCase):
    def _complete_audit(self):
        categories = {
            "credentials_profiles": "deployment/credential_gate.py",
            "market_polling": "actual_market_polling/service.py",
            "signals_strategy": "multi_timeframe_ai/service.py",
            "risk_approval": "risk_manager/service.py",
            "order_submission": "alpaca_paper_operations/engine.py",
            "order_lifecycle": "order_lifecycle/service.py",
            "positions_portfolio": "portfolio/position_manager.py",
            "session_orchestration": "paper_automation_controller/controller.py",
            "restart_recovery": "operations_manager/recovery.py",
            "end_of_day": "paper_runtime/end_of_day_v82_33_36.py",
            "monitoring_dashboard": "web_controller/operations_api.py",
            "paper_completion": "actual_validation/paper_completion.py",
        }
        records = []
        for category, path in categories.items():
            records.append(record(
                path,
                [category],
                submit=(category == "order_submission"),
                paper=(category == "order_submission"),
                live_off=(category == "order_submission"),
                score=10,
            ))
        return {"records": records}

    def test_complete_selection_passes(self):
        result = canonicalize(self._complete_audit())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["missing_categories"], [])

    def test_tests_are_excluded(self):
        audit = self._complete_audit()
        audit["records"].append(record(
            "tools/test_paper_trading_1_0_premarket_finalization.py",
            ["order_submission"],
            submit=True,
            score=9999,
        ))
        result = canonicalize(audit)
        self.assertNotIn(
            "tools/test_paper_trading_1_0_premarket_finalization.py",
            result["selected_write_paths"],
        )

    def test_release_is_excluded(self):
        audit = self._complete_audit()
        audit["records"].append(record(
            "release/v1/actual/engine.py",
            ["order_submission"],
            submit=True,
            score=9999,
        ))
        result = canonicalize(audit)
        self.assertNotIn(
            "release/v1/actual/engine.py",
            result["selected_write_paths"],
        )

    def test_unsafe_order_path_requires_review(self):
        audit = self._complete_audit()
        audit["records"] = [
            item for item in audit["records"]
            if "order_submission" not in item["categories"]
        ]
        audit["records"].append(record(
            "custom_order_engine/service.py",
            ["order_submission"],
            submit=True,
            paper=False,
            live_off=False,
            score=100,
        ))
        result = canonicalize(audit)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(
            result["unsafe_selected_paths"],
            ["custom_order_engine/service.py"],
        )

    def test_scope_locked(self):
        result = canonicalize(self._complete_audit())
        self.assertTrue(result["scope_locked"])
        self.assertFalse(result["new_feature_development_allowed"])
        self.assertFalse(result["actual_market_day_validation_performed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
