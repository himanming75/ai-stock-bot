import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.rollback_manifest_v75_1c import (
    RollbackManifestError,
    SCHEMA_VERSION,
    VERSION,
    build_rollback_manifest,
    canonical_json,
    main,
    sha256_of,
)


def source():
    manifest = {
        "status": "PASS",
        "decision": "promotion_manifest_created",
        "manifest_state": "READY_FOR_ROLLBACK_MANIFEST",
        "promotion_scope": "PROVISIONAL_PAPER_ONLY",
        "champion_candidate_id": "CAND-A",
        "runner_up_candidate_id": "CAND-B",
        "champion_score": 120.0,
        "runner_up_score": 110.0,
        "promotion_order": ["CAND-A", "CAND-B"],
        "activation_sequence": [
            {"sequence": 1, "action": "VERIFY_PROMOTION_PACKAGE_INTEGRITY"},
        ],
        "promotion_ledger": [
            {"ledger_index": 1, "event": "PROMOTION_MANIFEST_CREATED"},
        ],
        "integrity_verification": {"verified": True},
        "rollback_reference": {
            "required": True,
            "expected_version": "75.1C",
            "expected_state": "READY",
        },
        "paper_session_reference": {
            "activation_allowed": False,
            "expected_bootstrap_version": "75.2A",
            "state": "NOT_CREATED",
        },
        "requires_operator_review": True,
        "requires_rollback_manifest": True,
        "requires_paper_session_bootstrap": True,
        "created_at": "2026-07-30T00:00:00+00:00",
        "approved_for_live": False,
        "network_used": False,
        "source_promotion_package_sha256": "a" * 64,
        "schema_version": "v75.1b.promotion_manifest.1",
        "version": "75.1B",
        "activation_sequence_sha256": "b" * 64,
        "promotion_ledger_sha256": "c" * 64,
    }
    manifest["promotion_manifest_sha256"] = sha256_of(manifest)
    return manifest


class TestV751C(unittest.TestCase):
    def build(self):
        return build_rollback_manifest(
            source(), created_at="2026-07-30T00:00:00+00:00"
        )

    def test_version(self):
        self.assertEqual(VERSION, "75.1C")

    def test_schema(self):
        self.assertEqual(
            SCHEMA_VERSION,
            "v75.1c.rollback_manifest.1",
        )

    def test_pass(self):
        self.assertEqual(self.build()["status"], "PASS")

    def test_decision(self):
        self.assertEqual(
            self.build()["decision"], "rollback_manifest_created"
        )

    def test_state(self):
        self.assertEqual(
            self.build()["rollback_state"],
            "READY_FOR_PAPER_SESSION_BOOTSTRAP",
        )

    def test_champion(self):
        self.assertEqual(
            self.build()["champion_candidate_id"], "CAND-A"
        )

    def test_runner(self):
        self.assertEqual(
            self.build()["runner_up_candidate_id"], "CAND-B"
        )

    def test_sequence_first(self):
        self.assertEqual(
            self.build()["rollback_sequence"][0]["action"],
            "FREEZE_NEW_PAPER_ORDERS",
        )

    def test_sequence_last(self):
        self.assertEqual(
            self.build()["rollback_sequence"][-1]["action"],
            "VERIFY_RECOVERY_STATE",
        )

    def test_failover_step(self):
        actions = [
            x["action"] for x in self.build()["rollback_sequence"]
        ]
        self.assertIn("STAGE_RUNNER_UP_FAILOVER", actions)

    def test_policy(self):
        self.assertEqual(
            self.build()["rollback_policy"]["failover_policy"],
            "STAGE_RUNNER_UP",
        )

    def test_trigger_conditions(self):
        self.assertGreaterEqual(
            len(self.build()["trigger_conditions"]), 5
        )

    def test_bootstrap_allowed(self):
        self.assertTrue(
            self.build()["paper_session_reference"][
                "bootstrap_allowed"
            ]
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

    def test_recovery_pending(self):
        self.assertEqual(
            self.build()["recovery_verification"][
                "verification_state"
            ],
            "PENDING_EXECUTION",
        )

    def test_hash(self):
        result = self.build()
        copied = dict(result)
        observed = copied.pop("rollback_manifest_sha256")
        expected = hashlib.sha256(
            canonical_json(copied).encode("utf-8")
        ).hexdigest()
        self.assertEqual(observed, expected)

    def test_deterministic(self):
        self.assertEqual(self.build(), self.build())

    def test_bad_status(self):
        bad = source()
        bad["status"] = "FAIL"
        with self.assertRaises(RollbackManifestError):
            build_rollback_manifest(bad)

    def test_bad_schema(self):
        bad = source()
        bad["schema_version"] = "bad"
        with self.assertRaises(RollbackManifestError):
            build_rollback_manifest(bad)

    def test_bad_state(self):
        bad = source()
        bad["manifest_state"] = "BAD"
        with self.assertRaises(RollbackManifestError):
            build_rollback_manifest(bad)

    def test_bad_live(self):
        bad = source()
        bad["approved_for_live"] = True
        with self.assertRaises(RollbackManifestError):
            build_rollback_manifest(bad)

    def test_bad_network(self):
        bad = source()
        bad["network_used"] = True
        with self.assertRaises(RollbackManifestError):
            build_rollback_manifest(bad)

    def test_bad_integrity(self):
        bad = source()
        bad["promotion_manifest_sha256"] = "0" * 64
        with self.assertRaises(RollbackManifestError):
            build_rollback_manifest(bad)

    def test_bad_order(self):
        bad = source()
        bad["promotion_order"] = ["CAND-B", "CAND-A"]
        bad.pop("promotion_manifest_sha256")
        bad["promotion_manifest_sha256"] = sha256_of(bad)
        with self.assertRaises(RollbackManifestError):
            build_rollback_manifest(bad)

    def test_no_runner(self):
        data = source()
        data["runner_up_candidate_id"] = None
        data["runner_up_score"] = None
        data["promotion_order"] = ["CAND-A"]
        data.pop("promotion_manifest_sha256")
        data["promotion_manifest_sha256"] = sha256_of(data)
        result = build_rollback_manifest(
            data, created_at="2026-07-30T00:00:00+00:00"
        )
        self.assertEqual(
            result["rollback_policy"]["failover_policy"],
            "RETURN_TO_IDLE",
        )
        self.assertNotIn(
            "STAGE_RUNNER_UP_FAILOVER",
            [x["action"] for x in result["rollback_sequence"]],
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
                (out / "rollback_manifest_v75_1c.json").exists()
            )
            self.assertTrue(
                (out / "rollback_sequence_v75_1c.json").exists()
            )
            self.assertTrue(
                (out / "rollback_ledger_v75_1c.json").exists()
            )
            self.assertTrue(
                (out / "recovery_verification_v75_1c.json").exists()
            )
            self.assertTrue(
                (out / "rollback_manifest_v75_1c.sha256").exists()
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
