from __future__ import annotations

import unittest

from ai_engine_audit.canonicalizer import canonicalize_ai_engine


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
                rec("feature_engine/service.py", ["build_features"]),
                rec("signal_candidates/service.py", ["create_signal_candidates"]),
                rec("ai_signal_scoring/service.py", ["score_signal"]),
                rec("weighted_ensemble/service.py", ["weighted_ensemble"]),
                rec("multi_timeframe_ai/service.py", ["analyze_timeframes"]),
                rec("market_regime/service.py", ["detect_regime"]),
                rec("confidence_engine/service.py", ["calibrate_confidence"]),
                rec("explainability/service.py", ["build_explanation"]),
                rec("ranking_engine/service.py", ["rank_candidates"]),
                rec("portfolio_context_ai/service.py", ["correlation_context"]),
                rec("portfolio_optimizer_ai/service.py", ["optimize_portfolio"]),
                rec("offline_backtest_bridge/service.py", ["backtest_bridge"]),
                rec("multi_timeframe_ai/report.py", ["build_report"]),
            ]
        }

    def test_complete_pipeline(self):
        result = canonicalize_ai_engine(self._audit())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["missing_categories"], [])

    def test_test_files_excluded(self):
        audit = self._audit()
        audit["records"].append(
            rec("tools/test_fake_ai.py", ["weighted_ensemble"], score=99999)
        )
        result = canonicalize_ai_engine(audit)
        selected = result["selected"]["weighted_ensemble"]["selected"]["path"]
        self.assertNotEqual(selected, "tools/test_fake_ai.py")

    def test_release_files_excluded(self):
        audit = self._audit()
        audit["records"].append(
            rec("release/v1/actual/feature_engine.py", ["build_features"], score=99999)
        )
        result = canonicalize_ai_engine(audit)
        selected = result["selected"]["feature_engine"]["selected"]["path"]
        self.assertNotEqual(selected, "release/v1/actual/feature_engine.py")

    def test_scope_locked(self):
        result = canonicalize_ai_engine(self._audit())
        self.assertTrue(result["scope_locked"])
        self.assertFalse(result["new_ai_feature_development_allowed"])
        self.assertTrue(result["existing_ai_code_only"])

    def test_missing_category_review(self):
        audit = self._audit()
        audit["records"] = [
            item for item in audit["records"]
            if "backtest" not in item["path"]
        ]
        result = canonicalize_ai_engine(audit)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertIn("backtest_bridge", result["missing_categories"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
