import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.promotion_manifest_v75_1b import (
    PromotionManifestError,
    SCHEMA_VERSION,
    VERSION,
    build_promotion_manifest,
    canonical_json,
    main,
    sha256_of,
)


def candidate(role, cid, score):
    package = {
        "status": "PASS",
        "decision": "provisional_paper_candidate_packaged",
        "package_role": role,
        "candidate_id": cid,
        "strategy": "breakout",
        "revision_id": "REV-breakout-V72",
        "requalification_priority": 1 if role == "CHAMPION" else 2,
        "requalification_score": score,
        "parameters": {"p": 1 if role == "CHAMPION" else 2},
        "stage_evidence": [
            {"stage": "V68", "name": "a", "status": "PASS"},
            {"stage": "V70", "name": "b", "status": "PASS"},
            {"stage": "V71", "name": "c", "status": "PASS"},
        ],
        "promotion_scope": "PROVISIONAL_PAPER_ONLY",
        "paper_activation_state": "NOT_ACTIVATED",
        "requires_operator_review": True,
        "requires_rollback_package": True,
        "created_at": "2026-07-30T00:00:00+00:00",
        "approved_for_live": False,
        "network_used": False,
        "source_v74_report_sha256": "a" * 64,
        "schema_version": "v75.1a.champion_promotion_package.1",
        "version": "75.1A",
    }
    package["candidate_package_sha256"] = sha256_of(package)
    return package


def source():
    champion = candidate("CHAMPION", "CAND-A", 120.0)
    runner = candidate("RUNNER_UP", "CAND-B", 110.0)
    summary = {
        "status": "PASS",
        "decision": "champion_promotion_package_created",
        "package_state": "READY_FOR_PROMOTION_MANIFEST",
        "champion_candidate_id": "CAND-A",
        "runner_up_candidate_id": "CAND-B",
        "champion_score": 120.0,
        "runner_up_score": 110.0,
        "candidate_package_count": 2,
        "promotion_scope": "PROVISIONAL_PAPER_ONLY",
        "requires_promotion_manifest": True,
        "requires_rollback_manifest": True,
        "created_at": "2026-07-30T00:00:00+00:00",
        "approved_for_live": False,
        "network_used": False,
        "source_v74_report_sha256": "a" * 64,
        "schema_version": "v75.1a.champion_promotion_package.1",
        "version": "75.1A",
    }
    summary["promotion_summary_sha256"] = sha256_of(summary)

    bundle = {
        "status": "PASS",
        "decision": "champion_promotion_bundle_created",
        "package_state": "READY_FOR_PROMOTION_MANIFEST",
        "champion_package": champion,
        "runner_up_package": runner,
        "promotion_summary": summary,
        "created_at": "2026-07-30T00:00:00+00:00",
        "approved_for_live": False,
        "network_used": False,
        "source_v74_report_sha256": "a" * 64,
        "schema_version": "v75.1a.champion_promotion_package.1",
        "version": "75.1A",
    }
    bundle["promotion_package_sha256"] = sha256_of(bundle)
    return bundle


class TestV751B(unittest.TestCase):
    def build(self):
        return build_promotion_manifest(
            source(),
            created_at="2026-07-30T00:00:00+00:00",
        )

    def test_version(self):
        self.assertEqual(VERSION, "75.1B")

    def test_schema(self):
        self.assertEqual(
            SCHEMA_VERSION,
            "v75.1b.promotion_manifest.1",
        )

    def test_pass(self):
        self.assertEqual(self.build()["status"], "PASS")

    def test_decision(self):
        self.assertEqual(
            self.build()["decision"],
            "promotion_manifest_created",
        )

    def test_state(self):
        self.assertEqual(
            self.build()["manifest_state"],
            "READY_FOR_ROLLBACK_MANIFEST",
        )

    def test_champion(self):
        self.assertEqual(
            self.build()["champion_candidate_id"], "CAND-A"
        )

    def test_runner(self):
        self.assertEqual(
            self.build()["runner_up_candidate_id"], "CAND-B"
        )

    def test_order(self):
        self.assertEqual(
            self.build()["promotion_order"],
            ["CAND-A", "CAND-B"],
        )

    def test_activation_sequence(self):
        result = self.build()
        self.assertEqual(
            result["activation_sequence"][0]["action"],
            "VERIFY_PROMOTION_PACKAGE_INTEGRITY",
        )

    def test_last_activation_step(self):
        result = self.build()
        self.assertEqual(
            result["activation_sequence"][-1]["action"],
            "AWAIT_PAPER_SESSION_BOOTSTRAP",
        )

    def test_ledger(self):
        result = self.build()
        self.assertGreaterEqual(len(result["promotion_ledger"]), 3)

    def test_integrity_verified(self):
        self.assertTrue(
            self.build()["integrity_verification"]["verified"]
        )

    def test_rollback_required(self):
        self.assertTrue(self.build()["requires_rollback_manifest"])

    def test_bootstrap_required(self):
        self.assertTrue(
            self.build()["requires_paper_session_bootstrap"]
        )

    def test_activation_not_allowed(self):
        self.assertFalse(
            self.build()["paper_session_reference"][
                "activation_allowed"
            ]
        )

    def test_live_false(self):
        self.assertFalse(self.build()["approved_for_live"])

    def test_network_false(self):
        self.assertFalse(self.build()["network_used"])

    def test_hash(self):
        result = self.build()
        copied = dict(result)
        observed = copied.pop("promotion_manifest_sha256")
        expected = hashlib.sha256(
            canonical_json(copied).encode("utf-8")
        ).hexdigest()
        self.assertEqual(observed, expected)

    def test_deterministic(self):
        self.assertEqual(self.build(), self.build())

    def test_bad_status(self):
        bad = source()
        bad["status"] = "FAIL"
        with self.assertRaises(PromotionManifestError):
            build_promotion_manifest(bad)

    def test_bad_schema(self):
        bad = source()
        bad["schema_version"] = "bad"
        with self.assertRaises(PromotionManifestError):
            build_promotion_manifest(bad)

    def test_bad_state(self):
        bad = source()
        bad["package_state"] = "BAD"
        with self.assertRaises(PromotionManifestError):
            build_promotion_manifest(bad)

    def test_bad_live(self):
        bad = source()
        bad["approved_for_live"] = True
        with self.assertRaises(PromotionManifestError):
            build_promotion_manifest(bad)

    def test_bad_network(self):
        bad = source()
        bad["network_used"] = True
        with self.assertRaises(PromotionManifestError):
            build_promotion_manifest(bad)

    def test_bad_integrity(self):
        bad = source()
        bad["promotion_package_sha256"] = "0" * 64
        with self.assertRaises(PromotionManifestError):
            build_promotion_manifest(bad)

    def test_bad_champion_role(self):
        bad = source()
        bad["champion_package"]["package_role"] = "RUNNER_UP"
        bad["promotion_package_sha256"] = sha256_of(
            {k: v for k, v in bad.items() if k != "promotion_package_sha256"}
        )
        with self.assertRaises(PromotionManifestError):
            build_promotion_manifest(bad)

    def test_no_runner(self):
        data = source()
        data["runner_up_package"] = None
        data["promotion_summary"]["runner_up_candidate_id"] = None
        data["promotion_summary"]["runner_up_score"] = None
        data["promotion_summary"]["candidate_package_count"] = 1
        summary = data["promotion_summary"]
        summary.pop("promotion_summary_sha256")
        summary["promotion_summary_sha256"] = sha256_of(summary)
        data.pop("promotion_package_sha256")
        data["promotion_package_sha256"] = sha256_of(data)
        result = build_promotion_manifest(
            data,
            created_at="2026-07-30T00:00:00+00:00",
        )
        self.assertIsNone(result["runner_up_candidate_id"])
        self.assertEqual(result["promotion_order"], ["CAND-A"])

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
                (out / "promotion_manifest_v75_1b.json").exists()
            )
            self.assertTrue(
                (out / "activation_sequence_v75_1b.json").exists()
            )
            self.assertTrue(
                (out / "promotion_ledger_v75_1b.json").exists()
            )
            self.assertTrue(
                (out / "promotion_manifest_v75_1b.sha256").exists()
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
