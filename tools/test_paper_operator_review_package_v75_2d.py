from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from tools.paper_operator_review_package_v75_2d import (
    PaperOperatorReviewError,
    build_review_package,
    main,
    sha256_of,
)


def with_hash(obj, field):
    data = deepcopy(obj)
    data[field] = sha256_of(data)
    return data


def sample_preflight():
    checks = [
        {"check_index": 1, "check": "DEPLOYMENT_BUNDLE_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "REQUIRED_FILES", "state": "PASS", "verified_count": 2},
        {"check_index": 3, "check": "OFFLINE_RUNTIME_LOCKS", "state": "PASS"},
        {"check_index": 4, "check": "LAUNCH_PLAN_SEQUENCE", "state": "PASS"},
        {"check_index": 5, "check": "DEPLOYMENT_LEDGER_SEQUENCE", "state": "PASS"},
        {"check_index": 6, "check": "OPERATOR_REVIEW_GATE", "state": "REQUIRED"},
        {"check_index": 7, "check": "PAPER_SESSION_ACTIVATION", "state": "BLOCKED"},
    ]
    data = {
        "status": "PASS",
        "decision": "paper_deployment_preflight_passed",
        "preflight_state": "READY_FOR_OPERATOR_REVIEW",
        "preflight_id": "PDP-0123456789ABCDEF",
        "bundle_id": "PDB-0123456789ABCDEF",
        "session_id": "PAPER-0123456789ABCDEF",
        "champion_candidate_id": "CAND-A",
        "verified_files": [
            {"inventory_index": 1, "path": "a.json", "required": True, "exists": True, "verification_state": "VERIFIED"},
            {"inventory_index": 2, "path": "b.json", "required": True, "exists": True, "verification_state": "VERIFIED"},
        ],
        "preflight_checks": checks,
        "preflight_ledger": [],
        "preflight_checklist_sha256": sha256_of(checks),
        "preflight_ledger_sha256": sha256_of([]),
        "source_paper_deployment_bundle_sha256": "a" * 64,
        "operator_review": {"required": True, "state": "PENDING", "approval_recorded": False},
        "activation_gate": {"activation_allowed": False, "next_version": "75.2D", "operator_review_required": True},
        "safety_lock": {
            "network_enabled": False,
            "live_orders_enabled": False,
            "broker_credentials_required": False,
            "external_side_effects_allowed": False,
            "lock_state": "ENFORCED",
        },
        "approved_for_live": False,
        "network_used": False,
        "created_at": "2026-07-30T00:00:00+00:00",
        "schema_version": "v75.2c.paper_deployment_preflight.1",
        "version": "75.2C",
    }
    return with_hash(data, "paper_deployment_preflight_sha256")


def sample_account():
    data = {
        "account_state": "INITIALIZED",
        "cash": 100000.0,
        "closed_orders": [],
        "currency": "USD",
        "equity": 100000.0,
        "max_positions": 10,
        "open_orders": [],
        "positions": [],
        "realized_pnl": 0.0,
        "starting_cash": 100000.0,
        "unrealized_pnl": 0.0,
    }
    return with_hash(data, "account_state_sha256")


def sample_health():
    data = {
        "account_initialized": True,
        "bootstrap_integrity": "PASS",
        "champion_attached": True,
        "health_state": "READY",
        "live_orders_disabled": True,
        "network_disabled": True,
        "paper_activation_state": "NOT_ACTIVATED",
        "rollback_manifest_attached": True,
        "session_id": "PAPER-0123456789ABCDEF",
    }
    return with_hash(data, "health_check_sha256")


def sample_config():
    return {
        "activation_allowed": False,
        "allowed_operator_decisions": ["APPROVE_PAPER", "REJECT", "HOLD"],
        "automatic_approval_allowed": False,
        "network_enabled": False,
        "operator_signature_required": True,
        "required_review_items": [
            "CONFIRM_CHAMPION_CANDIDATE",
            "CONFIRM_INITIAL_PAPER_ACCOUNT",
            "CONFIRM_SESSION_HEALTH_READY",
            "CONFIRM_OFFLINE_NETWORK_LOCK",
            "CONFIRM_LIVE_ORDERS_DISABLED",
        ],
    }


class TestV752D(unittest.TestCase):
    def build(self):
        return build_review_package(
            sample_preflight(), sample_account(), sample_health(), sample_config(),
            created_at="2026-07-30T01:02:03+00:00",
        )

    def test_pass(self):
        self.assertEqual(self.build()["status"], "PASS")

    def test_version_schema(self):
        result = self.build()
        self.assertEqual(result["version"], "75.2D")
        self.assertEqual(result["schema_version"], "v75.2d.paper_operator_review_package.1")

    def test_state(self):
        self.assertEqual(self.build()["review_state"], "AWAITING_OPERATOR_DECISION")

    def test_decision_pending(self):
        decision = self.build()["operator_decision"]
        self.assertEqual(decision["decision_state"], "PENDING")
        self.assertFalse(decision["decision_recorded"])
        self.assertIsNone(decision["selected_decision"])

    def test_activation_blocked(self):
        self.assertFalse(self.build()["activation_gate"]["activation_allowed"])

    def test_live_false(self):
        self.assertFalse(self.build()["approved_for_live"])

    def test_network_false(self):
        self.assertFalse(self.build()["network_used"])

    def test_checklist_pending(self):
        for item in self.build()["review_checklist"]:
            self.assertFalse(item["operator_confirmed"])
            self.assertEqual(item["state"], "PENDING_OPERATOR_CONFIRMATION")

    def test_summary(self):
        summary = self.build()["review_summary"]
        self.assertEqual(summary["starting_cash"], 100000.0)
        self.assertEqual(summary["verified_file_count"], 2)
        self.assertEqual(summary["paper_activation_state"], "NOT_ACTIVATED")

    def test_ledger(self):
        ledger = self.build()["review_ledger"]
        self.assertEqual([x["ledger_index"] for x in ledger], list(range(1, 7)))
        self.assertEqual(ledger[-1]["state"], "BLOCKED")

    def test_hash(self):
        result = self.build()
        observed = result.pop("paper_operator_review_package_sha256")
        self.assertEqual(observed, sha256_of(result))

    def test_deterministic_id(self):
        self.assertEqual(self.build()["review_id"], self.build()["review_id"])

    def test_bad_preflight_integrity(self):
        p = sample_preflight(); p["bundle_id"] = "tampered"
        with self.assertRaises(PaperOperatorReviewError):
            build_review_package(p, sample_account(), sample_health(), sample_config())

    def test_bad_preflight_state(self):
        p = sample_preflight(); p.pop("paper_deployment_preflight_sha256"); p["preflight_state"] = "BAD"; p = with_hash(p, "paper_deployment_preflight_sha256")
        with self.assertRaises(PaperOperatorReviewError):
            build_review_package(p, sample_account(), sample_health(), sample_config())

    def test_bad_account_integrity(self):
        a = sample_account(); a["cash"] = 1.0
        with self.assertRaises(PaperOperatorReviewError):
            build_review_package(sample_preflight(), a, sample_health(), sample_config())

    def test_nonempty_positions(self):
        a = sample_account(); a.pop("account_state_sha256"); a["positions"] = [{"symbol": "AAPL"}]; a = with_hash(a, "account_state_sha256")
        with self.assertRaises(PaperOperatorReviewError):
            build_review_package(sample_preflight(), a, sample_health(), sample_config())

    def test_bad_health_integrity(self):
        h = sample_health(); h["health_state"] = "BAD"
        with self.assertRaises(PaperOperatorReviewError):
            build_review_package(sample_preflight(), sample_account(), h, sample_config())

    def test_health_session_mismatch(self):
        h = sample_health(); h.pop("health_check_sha256"); h["session_id"] = "PAPER-OTHER"; h = with_hash(h, "health_check_sha256")
        with self.assertRaises(PaperOperatorReviewError):
            build_review_package(sample_preflight(), sample_account(), h, sample_config())

    def test_bad_config(self):
        c = sample_config(); c["automatic_approval_allowed"] = True
        with self.assertRaises(PaperOperatorReviewError):
            build_review_package(sample_preflight(), sample_account(), sample_health(), c)

    def test_main_success_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name, data in (
                ("preflight.json", sample_preflight()),
                ("account.json", sample_account()),
                ("health.json", sample_health()),
                ("config.json", sample_config()),
            ):
                (root / name).write_text(json.dumps(data), encoding="utf-8")
            rc = main([
                "--input", str(root / "preflight.json"),
                "--account-state", str(root / "account.json"),
                "--session-health", str(root / "health.json"),
                "--config", str(root / "config.json"),
                "--output-dir", str(root / "out"),
            ])
            self.assertEqual(rc, 0)
            self.assertTrue((root / "out" / "paper_operator_review_package_v75_2d.json").is_file())
            rc = main([
                "--input", str(root / "missing.json"),
                "--account-state", str(root / "account.json"),
                "--session-health", str(root / "health.json"),
                "--config", str(root / "config.json"),
                "--output-dir", str(root / "out2"),
            ])
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
