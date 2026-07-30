import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.champion_promotion_package_v75_1a import (
    PromotionPackageError,
    SCHEMA_VERSION,
    VERSION,
    build_promotion_package,
    canonical_json,
    main,
)


def stage(stage_id):
    data = {
        "stage": stage_id,
        "name": {
            "V68": "analytics_revalidation",
            "V70": "walk_forward_revalidation",
            "V71": "monte_carlo_revalidation",
        }[stage_id],
        "status": "PASS",
    }
    if stage_id == "V70":
        data["validation_state"] = "APPROVED"
        data["pass_rate"] = 1.0
    if stage_id == "V71":
        data["validation_state"] = "APPROVED"
        data["probability_positive"] = 1.0
        data["p05_net_pnl"] = 100.0
    return data


def result(cid, priority, score):
    return {
        "candidate_id": cid,
        "requalification_priority": priority,
        "parameters": {"threshold": priority},
        "requalification_state": "APPROVED",
        "stage_results": [stage("V68"), stage("V70"), stage("V71")],
        "requalification_score": score,
        "eligible_for_provisional_paper_promotion": True,
        "approved_for_live": False,
    }


def source():
    return {
        "status": "PASS",
        "decision": "candidate_requalification_completed",
        "pipeline_state": "APPROVED_SURVIVORS_AVAILABLE",
        "champion_strategy": "breakout",
        "revision_id": "REV-breakout-V72",
        "selected_candidate_count": 2,
        "approved_candidate_count": 2,
        "rejected_candidate_count": 0,
        "champion_candidate_id": "CAND-A",
        "runner_up_candidate_id": "CAND-B",
        "execution_results": [
            result("CAND-A", 1, 120.0),
            result("CAND-B", 2, 110.0),
        ],
        "approved_candidate_ids": ["CAND-A", "CAND-B"],
        "requires_provisional_paper_review": True,
        "approved_for_live": False,
        "network_used": False,
        "candidate_requalification_report_sha256": "a" * 64,
        "schema_version": "v74.candidate_requalification_pipeline.1",
        "version": "74.0",
    }


class TestV751A(unittest.TestCase):
    def build(self):
        return build_promotion_package(
            source(), created_at="2026-07-30T00:00:00+00:00"
        )

    def test_version(self):
        self.assertEqual(VERSION, "75.1A")

    def test_schema(self):
        self.assertEqual(
            SCHEMA_VERSION,
            "v75.1a.champion_promotion_package.1",
        )

    def test_pass(self):
        self.assertEqual(self.build()["status"], "PASS")

    def test_decision(self):
        self.assertEqual(
            self.build()["decision"],
            "champion_promotion_bundle_created",
        )

    def test_champion(self):
        self.assertEqual(
            self.build()["champion_package"]["candidate_id"],
            "CAND-A",
        )

    def test_runner_up(self):
        self.assertEqual(
            self.build()["runner_up_package"]["candidate_id"],
            "CAND-B",
        )

    def test_roles(self):
        result = self.build()
        self.assertEqual(
            result["champion_package"]["package_role"], "CHAMPION"
        )
        self.assertEqual(
            result["runner_up_package"]["package_role"], "RUNNER_UP"
        )

    def test_scope(self):
        self.assertEqual(
            self.build()["promotion_summary"]["promotion_scope"],
            "PROVISIONAL_PAPER_ONLY",
        )

    def test_live_false(self):
        result = self.build()
        self.assertFalse(result["approved_for_live"])
        self.assertFalse(result["champion_package"]["approved_for_live"])
        self.assertFalse(result["runner_up_package"]["approved_for_live"])

    def test_network_false(self):
        result = self.build()
        self.assertFalse(result["network_used"])
        self.assertFalse(result["champion_package"]["network_used"])
        self.assertFalse(result["runner_up_package"]["network_used"])

    def test_stage_evidence(self):
        stages = self.build()["champion_package"]["stage_evidence"]
        self.assertEqual(
            [x["stage"] for x in stages],
            ["V68", "V70", "V71"],
        )

    def test_score_order(self):
        result = self.build()["promotion_summary"]
        self.assertGreaterEqual(
            result["champion_score"], result["runner_up_score"]
        )

    def test_hash(self):
        result = self.build()
        copied = dict(result)
        observed = copied.pop("promotion_package_sha256")
        expected = hashlib.sha256(
            canonical_json(copied).encode("utf-8")
        ).hexdigest()
        self.assertEqual(observed, expected)

    def test_deterministic(self):
        self.assertEqual(self.build(), self.build())

    def test_bad_status(self):
        bad = source()
        bad["status"] = "FAIL"
        with self.assertRaises(PromotionPackageError):
            build_promotion_package(bad)

    def test_bad_schema(self):
        bad = source()
        bad["schema_version"] = "bad"
        with self.assertRaises(PromotionPackageError):
            build_promotion_package(bad)

    def test_bad_pipeline_state(self):
        bad = source()
        bad["pipeline_state"] = "NO_APPROVED_SURVIVORS"
        with self.assertRaises(PromotionPackageError):
            build_promotion_package(bad)

    def test_bad_live(self):
        bad = source()
        bad["approved_for_live"] = True
        with self.assertRaises(PromotionPackageError):
            build_promotion_package(bad)

    def test_bad_network(self):
        bad = source()
        bad["network_used"] = True
        with self.assertRaises(PromotionPackageError):
            build_promotion_package(bad)

    def test_missing_champion(self):
        bad = source()
        bad["champion_candidate_id"] = None
        with self.assertRaises(PromotionPackageError):
            build_promotion_package(bad)

    def test_champion_not_approved(self):
        bad = source()
        bad["execution_results"][0]["requalification_state"] = "REJECTED"
        with self.assertRaises(PromotionPackageError):
            build_promotion_package(bad)

    def test_bad_stage_sequence(self):
        bad = source()
        bad["execution_results"][0]["stage_results"].reverse()
        with self.assertRaises(PromotionPackageError):
            build_promotion_package(bad)

    def test_failed_stage(self):
        bad = source()
        bad["execution_results"][0]["stage_results"][0]["status"] = "FAIL"
        with self.assertRaises(PromotionPackageError):
            build_promotion_package(bad)

    def test_runner_higher_score(self):
        bad = source()
        bad["execution_results"][1]["requalification_score"] = 130.0
        with self.assertRaises(PromotionPackageError):
            build_promotion_package(bad)

    def test_no_runner_up_allowed(self):
        data = source()
        data["runner_up_candidate_id"] = None
        data["approved_candidate_ids"] = ["CAND-A"]
        data["approved_candidate_count"] = 1
        data["execution_results"] = [data["execution_results"][0]]
        result = build_promotion_package(
            data, created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertIsNone(result["runner_up_package"])
        self.assertEqual(
            result["promotion_summary"]["candidate_package_count"], 1
        )

    def test_main_success(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "input.json"
            out = root / "out"
            inp.write_text(json.dumps(source()), encoding="utf-8")
            code = main([
                "--input", str(inp),
                "--output-dir", str(out),
            ])
            self.assertEqual(code, 0)
            self.assertTrue(
                (out / "promotion_package_v75_1a.json").exists()
            )
            self.assertTrue(
                (out / "champion_package_v75_1a.json").exists()
            )
            self.assertTrue(
                (out / "runner_up_package_v75_1a.json").exists()
            )
            self.assertTrue(
                (out / "promotion_summary_v75_1a.json").exists()
            )
            self.assertTrue(
                (out / "promotion_package_v75_1a.sha256").exists()
            )

    def test_main_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code = main([
                "--input", str(root / "missing.json"),
                "--output-dir", str(root / "out"),
            ])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
